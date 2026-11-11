"""Apply a Kitaru replay's override and tool policy to a StudyBot turn.

What StudyBot supports (checked up front by `ReplayPlan.check`, before any model call):

    override.model         str (every model call) or {old: new} map. OpenAI models only.
    override.model_params  temperature, top_p, max_tokens, seed
    override.prompt        replaces the user's question for the whole turn
    override.system_prompt replaces the tutor's whole prompt (scope, task rules, tools guidance).

    tool policy            passthrough | history | static, on_miss fail | error_result | passthrough
                           llm is rejected.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from kitaru.api_models.v1.replay_config import (
    HistoryConfig,
    HistoryScope,
    LLMConfig,
    PassthroughConfig,
    ReplayOverride,
    StaticConfig,
    StaticMatchMode,
    ToolPolicy,
    ToolPolicyOnMiss,
)
from kitaru.api_models.v1.replay import ToolLookupRequest, ToolLookupResponse
from kitaru.api_models.v1.session_node import NodeStatus
from kitaru.cache_keys import compute_tool_cache_key

TOOL_NAMES = frozenset({"search_lessons", "get_code_example", "get_mock_progress"})
MODEL_PARAMS = frozenset({"temperature", "top_p", "max_tokens", "seed"})
OPENAI_PREFIX = "openai:"


class ReplayConfigError(ValueError):
    """The replay asks for something StudyBot can't do. Raised before any model call."""


class ToolPolicyMissError(RuntimeError):
    """A history/static policy had no answer and on_miss is 'fail'."""


class RecordedToolFailure(RuntimeError):
    """The recorded call failed, so the replayed call fails the same way."""


def model_name(identifier: str) -> str:
    """'openai:gpt-4o-mini' or 'gpt-4o-mini' -> 'gpt-4o-mini'. Other providers are rejected."""
    if ":" in identifier:
        if not identifier.startswith(OPENAI_PREFIX):
            raise ReplayConfigError(f"Only OpenAI models are supported, got '{identifier}'")
        identifier = identifier[len(OPENAI_PREFIX) :]
    if not identifier:
        raise ReplayConfigError("Empty model name in override")
    return identifier


@dataclass
class ToolDecision:
    run_live: bool
    result: Any = None
    policy: str = "passthrough"
    hit: bool | None = None  # None for passthrough


Lookup = Callable[[str, str, int | None], Awaitable[ToolLookupResponse]]


@dataclass
class ReplayPlan:
    override: ReplayOverride | None
    tool_policy: ToolPolicy
    lookup: Lookup  # (tool_name, cache_key, occurrence) -> response
    _occurrences: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_replay(cls, replay: Any, client: Any) -> "ReplayPlan":
        async def lookup(tool_name: str, cache_key: str, occurrence: int | None) -> ToolLookupResponse:
            request = ToolLookupRequest(tool_name=tool_name, cache_key=cache_key, occurrence=occurrence)
            return await client.replays.tool_lookup(replay.id, request)

        plan = cls(override=replay.override, tool_policy=replay.tool_policy, lookup=lookup)
        plan.check()
        return plan

    # ---------- up-front checks ----------

    def check(self) -> None:
        o = self.override
        if o is not None:
            if isinstance(o.model, str):
                model_name(o.model)
            elif isinstance(o.model, dict):
                for old, new in o.model.items():
                    model_name(old), model_name(new)
            unsupported = sorted(set(o.model_params or {}) - MODEL_PARAMS)
            if unsupported:
                raise ReplayConfigError(f"Unsupported model_params: {', '.join(unsupported)}")
            if o.prompt is not None and not o.prompt.strip():
                raise ReplayConfigError("Override prompt is empty")
            if o.system_prompt is not None and not o.system_prompt.strip():
                raise ReplayConfigError("Override system_prompt is empty")
        unknown = sorted(set(self.tool_policy.tools) - TOOL_NAMES)
        if unknown:
            raise ReplayConfigError(f"Tool policy names unknown tools: {', '.join(unknown)}")
        for name, config in [("default", self.tool_policy.default), *self.tool_policy.tools.items()]:
            if isinstance(config, LLMConfig):
                raise ReplayConfigError(f"The 'llm' tool policy is not supported (tool: {name})")

    # ---------- model overrides ----------

    def model_for(self, requested: str) -> str | None:
        """Replacement model name for a call that asked for `requested`, or None to keep it."""
        model = self.override.model if self.override else None
        if isinstance(model, str):
            return model_name(model)
        if isinstance(model, dict):
            wanted = model_name(requested)
            for old, new in model.items():
                if model_name(old) == wanted:
                    return model_name(new)
        return None

    def model_params(self) -> dict:
        return dict(self.override.model_params or {}) if self.override else {}

    # ---------- tool policies ----------

    def _config(self, tool_name: str):
        return self.tool_policy.tools.get(tool_name, self.tool_policy.default)

    async def decide_tool(self, tool_name: str, recorded_args: Any) -> ToolDecision:
        """What a replayed tool call gets. recorded_args must be captured the same way as when recording."""
        config = self._config(tool_name)
        if isinstance(config, PassthroughConfig):
            return ToolDecision(run_live=True)
        if isinstance(config, StaticConfig):
            for case in config.cases:
                if _static_matches(case.match, case.match_mode, recorded_args):
                    return ToolDecision(run_live=False, result=case.result, policy="static", hit=True)
            return self._miss("static", config.on_miss, tool_name)
        if isinstance(config, HistoryConfig):
            return await self._history(tool_name, recorded_args, config)
        raise ReplayConfigError(f"Unsupported tool policy for {tool_name}: {type(config).__name__}")

    async def _history(self, tool_name: str, recorded_args: Any, config: HistoryConfig) -> ToolDecision:
        cache_key = compute_tool_cache_key(tool_name, recorded_args)
        if cache_key is None:
            return self._miss("history", config.on_miss, tool_name)
        baseline = config.scope == HistoryScope.BASELINE
        occurrence = self._occurrences.get(cache_key, 0) if baseline else None
        response = await self.lookup(tool_name, cache_key, occurrence)
        if response.match is None:
            return self._miss("history", config.on_miss, tool_name)
        if baseline:  # advance only on a hit, so identical calls replay their own results in order
            self._occurrences[cache_key] = occurrence + 1
        if response.match.status == NodeStatus.FAILED:
            raise RecordedToolFailure(f"Recorded {tool_name} call failed: {response.match.error}")
        return ToolDecision(run_live=False, result=response.match.result, policy="history", hit=True)

    def _miss(self, policy: str, on_miss: ToolPolicyOnMiss, tool_name: str) -> ToolDecision:
        if on_miss == ToolPolicyOnMiss.PASSTHROUGH:
            return ToolDecision(run_live=True, policy=policy, hit=False)
        message = f"No {policy} result for tool '{tool_name}'"
        if on_miss == ToolPolicyOnMiss.ERROR_RESULT:
            return ToolDecision(run_live=False, result={"error": message}, policy=policy, hit=False)
        raise ToolPolicyMissError(message)


def _static_matches(match: Any, mode: StaticMatchMode, args: Any) -> bool:
    if match is None:
        return True  # a case without a match answers every call
    if mode == StaticMatchMode.EXACT:
        return match == args
    # subset: every key in match appears in args with an equal value (shallow)
    return isinstance(match, dict) and isinstance(args, dict) and all(
        k in args and args[k] == v for k, v in match.items()
    )
