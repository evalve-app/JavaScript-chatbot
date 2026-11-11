"""PydanticAI capability that records model and tool calls into the current turn.

Pass one per agent run:

    await agent.run(..., capabilities=[RecordingHooks(recorder, parent=span_id)])

Uses only public PydanticAI hooks (wrap_model_request, wrap_tool_execute).
Recording never changes what the agent sees: results and errors pass through unchanged.
"""

import dataclasses
from collections.abc import Callable
from typing import Any

from kitaru.api_models.v1.session import TokenUsage
from kitaru.api_models.v1.session_node import NodeType
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse

from app.recording.context import trace_parent
from app.recording.recorder import TurnRecorder, utcnow
from app.recording.replay import ReplayPlan

RECORDED_SETTINGS = ("temperature", "max_tokens", "top_p", "seed")


def project_part(part: Any) -> dict:
    """A message part as plain data. Only the fields a reviewer needs."""
    kind = part.part_kind
    if kind in ("user-prompt", "system-prompt", "text", "thinking", "retry-prompt"):
        return {"type": kind, "content": part.content}
    if kind == "tool-call":
        return {"type": kind, "tool_name": part.tool_name, "args": part.args, "tool_call_id": part.tool_call_id}
    if kind == "tool-return":
        return {"type": kind, "tool_name": part.tool_name, "content": part.content, "tool_call_id": part.tool_call_id}
    return {"type": kind}  # unknown part kinds: record the kind only


def project_messages(messages: list[ModelMessage]) -> list[dict]:
    projected = []
    for message in messages:
        entry: dict[str, Any] = {"kind": message.kind, "parts": [project_part(p) for p in message.parts]}
        if isinstance(message, ModelRequest) and message.instructions:
            entry["instructions"] = message.instructions
        projected.append(entry)
    return projected


def model_inputs(messages: list[ModelMessage]) -> tuple[dict, str | None, str | None]:
    """(inputs, input_text_selector, system_prompt_selector) for an llm_call node."""
    projected = project_messages(messages)
    inputs: dict[str, Any] = {"messages": projected}
    system_selector = None
    last_request = next((m for m in reversed(messages) if isinstance(m, ModelRequest)), None)
    if last_request is not None and last_request.instructions:
        inputs["instructions"] = last_request.instructions
        system_selector = "/instructions"
    input_selector = None
    for i in range(len(projected) - 1, -1, -1):
        parts = projected[i]["parts"]
        j = next((k for k in range(len(parts) - 1, -1, -1) if parts[k]["type"] == "user-prompt"), None)
        if j is not None and isinstance(parts[j]["content"], str):
            input_selector = f"/messages/{i}/parts/{j}/content"
            break
    return inputs, input_selector, system_selector


def model_outputs(response: ModelResponse) -> dict:
    text = "".join(p.content for p in response.parts if p.part_kind == "text")
    return {
        "text": text or None,
        "parts": [project_part(p) for p in response.parts],
        "finish_reason": response.finish_reason,
    }


def token_usage(response: ModelResponse) -> TokenUsage:
    usage = response.usage
    return TokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_input_tokens=usage.cache_read_tokens,
    )


class RecordingHooks(AbstractCapability[Any]):
    """Per agent run: records into one TurnRecorder under one parent span.

    With a ReplayPlan, also applies model/model_params overrides and tool policies.
    """

    def __init__(
        self,
        recorder: TurnRecorder,
        parent: str,
        agent_name: str,
        replay: ReplayPlan | None = None,
        model_factory: Callable[[str], Any] | None = None,
    ):
        self.recorder = recorder
        self.parent = parent
        self.agent_name = agent_name
        self.replay = replay
        if model_factory is None:
            from app.agents.models import chat_model_named

            model_factory = chat_model_named
        self.model_factory = model_factory

    def _apply_overrides(self, request_context):
        """Swap model / settings for a replay. Returns (request_context, override note or None)."""
        if self.replay is None:
            return request_context, None
        changes: dict[str, Any] = {}
        note: dict[str, Any] = {}
        new_model = self.replay.model_for(request_context.model.model_name)
        if new_model and new_model != request_context.model.model_name:
            changes["model"] = self.model_factory(new_model)
            note["model"] = new_model
        params = self.replay.model_params()
        if params:
            changes["model_settings"] = {**(request_context.model_settings or {}), **params}
            note["model_params"] = params
        if not changes:
            return request_context, None
        return dataclasses.replace(request_context, **changes), note

    async def wrap_model_request(self, ctx, *, request_context, handler):
        started = utcnow()
        requested = request_context.model.model_name
        request_context, override_note = self._apply_overrides(request_context)
        inputs, input_selector, system_selector = model_inputs(request_context.messages)
        settings = request_context.model_settings or {}
        attributes: dict[str, Any] = {
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": "openai",
            "gen_ai.agent.name": self.agent_name,
            "gen_ai.request.model": requested,
        }
        if override_note:
            attributes["replay.override"] = override_note
        common = dict(
            node_type=NodeType.LLM_CALL,
            name=f"chat {requested}",  # OpenTelemetry GenAI span name: "{operation} {model}"
            parent=self.parent,
            started_at=started,
            inputs=inputs,
            input_text_selector=input_selector,
            system_prompt_selector=system_selector,
            requested_model=requested,
            model_params={k: settings[k] for k in RECORDED_SETTINGS if k in settings} or None,
            attributes=attributes,
        )
        try:
            response = await handler(request_context)
        except BaseException as error:
            self.recorder.add_node(**common, error=error)
            raise
        outputs = model_outputs(response)
        usage = token_usage(response)
        attributes.update(
            {
                "gen_ai.response.model": response.model_name,
                "gen_ai.response.finish_reasons": [response.finish_reason] if response.finish_reason else [],
                "gen_ai.usage.input_tokens": usage.input_tokens,
                "gen_ai.usage.output_tokens": usage.output_tokens,
            }
        )
        self.recorder.add_node(
            **common,
            outputs=outputs,
            output_text_selector="/text" if outputs["text"] else None,
            model=response.model_name,
            model_provider=response.provider_name,
            tokens=usage,
        )
        return response

    async def wrap_tool_execute(self, ctx, *, call, tool_def, args, handler):
        # Recorded inputs and history lookups use the same captured form, so cache keys match.
        recorded_args = self.recorder.capture(args)
        node_id = self.recorder.begin_node(
            NodeType.TOOL_CALL,
            f"execute_tool {call.tool_name}",  # OpenTelemetry GenAI span name
            parent=self.parent,
            inputs=recorded_args,
            tool_name=call.tool_name,
            attributes={
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.tool.name": call.tool_name,
                "gen_ai.tool.call.id": call.tool_call_id,
                "gen_ai.tool.type": "function",
                "gen_ai.agent.name": self.agent_name,
            },
        )
        replay_attributes: dict[str, Any] = {}
        try:
            # Steps the tool records itself (e.g. retrieval) nest under this node.
            with trace_parent(self.recorder, node_id):
                if self.replay is None:
                    result = await handler(args)
                else:
                    decision = await self.replay.decide_tool(call.tool_name, recorded_args)
                    replay_attributes["replay.policy"] = decision.policy
                    if decision.hit is not None:
                        replay_attributes["replay.policy_hit"] = decision.hit
                    replay_attributes["replay.mocked"] = not decision.run_live
                    result = await handler(args) if decision.run_live else decision.result
        except BaseException as error:
            self.recorder.end_node(node_id, error=error, attributes=replay_attributes)
            raise
        self.recorder.end_node(node_id, outputs=result, attributes=replay_attributes)
        return result
