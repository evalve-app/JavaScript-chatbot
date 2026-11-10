"""Fake LLMs for tests (no OpenAI calls)."""

from collections.abc import Iterator
from contextlib import contextmanager

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from app.agents.classifier import classifier_agent
from app.agents.tutor import tutor_agent


def fake_classifier_model(scope: str, intent: str, language: str) -> TestModel:
    return TestModel(custom_output_args={"scope": scope, "intent": intent, "language": language})


def scripted_tutor_model(tool_calls: list[tuple[str, dict]] | None = None, answer: str = "Fake answer") -> FunctionModel:
    """Calls the given tools (in one step), then returns `answer`."""
    tool_calls = tool_calls or []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        last = messages[-1]
        already_called = isinstance(last, ModelRequest) and any(isinstance(p, ToolReturnPart) for p in last.parts)
        if tool_calls and not already_called:
            return ModelResponse(parts=[ToolCallPart(name, args) for name, args in tool_calls])
        return ModelResponse(parts=[TextPart(answer)])

    return FunctionModel(respond)


@contextmanager
def fake_agents(
    classification: tuple[str, str, str] = ("in_scope", "concept", "javascript"),
    tool_calls: list[tuple[str, dict]] | None = None,
    answer: str = "Fake answer",
) -> Iterator[None]:
    with (
        classifier_agent.override(model=fake_classifier_model(*classification)),
        tutor_agent.override(model=scripted_tutor_model(tool_calls, answer)),
    ):
        yield
