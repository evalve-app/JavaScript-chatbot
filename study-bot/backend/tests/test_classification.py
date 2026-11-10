import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agents.classifier import Classification, build_classifier_input, classifier_agent
from app.agents.workflow import select_route


def test_valid_classification():
    c = Classification(scope="in_scope", intent="debugging", language="javascript")
    assert c.model_dump() == {"scope": "in_scope", "intent": "debugging", "language": "javascript"}


@pytest.mark.parametrize(
    "data",
    [
        {"scope": "maybe", "intent": "concept", "language": "javascript"},
        {"scope": "in_scope", "intent": "chitchat", "language": "javascript"},
        {"scope": "in_scope", "intent": "concept", "language": "python"},
        {"scope": "in_scope", "intent": "concept"},
        {"scope": "in_scope", "intent": "concept", "language": "javascript", "extra": 1},
    ],
)
def test_invalid_classification_rejected(data):
    with pytest.raises(ValidationError):
        Classification(**data)


def test_classifier_output_schema_has_only_allowed_values():
    schema = Classification.model_json_schema()
    assert set(schema["properties"]) == {"scope", "intent", "language"}
    assert set(schema["properties"]["intent"]["enum"]) == {"concept", "debugging", "code_generation", "quiz"}


@pytest.mark.anyio
async def test_classifier_returns_validated_structured_output():
    seen_prompts = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen_prompts.append(messages[-1].parts[-1].content)
        tool = info.output_tools[0]
        return ModelResponse(
            parts=[ToolCallPart(tool.name, {"scope": "in_scope", "intent": "concept", "language": "javascript"})]
        )

    history = [("user", "Explain JavaScript closures."), ("assistant", "A closure is...")]
    with classifier_agent.override(model=FunctionModel(respond)):
        result = await classifier_agent.run(build_classifier_input("Can you show another example?", history))

    assert result.output == Classification(scope="in_scope", intent="concept", language="javascript")
    # Follow-ups include recent context so the classifier can resolve them.
    assert "Explain JavaScript closures." in seen_prompts[0]
    assert "Can you show another example?" in seen_prompts[0]


@pytest.mark.anyio
async def test_classifier_retries_on_invalid_output():
    calls = {"n": 0}

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls["n"] += 1
        args = (
            {"scope": "sure", "intent": "concept", "language": "javascript"}
            if calls["n"] == 1
            else {"scope": "out_of_scope", "intent": "concept", "language": "unknown"}
        )
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    with classifier_agent.override(model=FunctionModel(respond)):
        result = await classifier_agent.run("Best pizza in town?")
    assert result.output.scope == "out_of_scope"
    assert calls["n"] == 2


def test_build_classifier_input_without_history():
    assert build_classifier_input("Explain closures", []) == "New message:\nExplain closures"


@pytest.mark.parametrize(
    ("scope", "intent", "language", "route"),
    [
        ("in_scope", "concept", "javascript", "concept"),
        ("in_scope", "debugging", "javascript", "debugging"),
        ("in_scope", "code_generation", "javascript", "code_generation"),
        ("in_scope", "quiz", "javascript", "quiz"),
        ("out_of_scope", "concept", "unknown", "out_of_scope"),
        ("out_of_scope", "concept", "other", "out_of_scope_other_language"),
    ],
)
def test_select_route(scope, intent, language, route):
    assert select_route(Classification(scope=scope, intent=intent, language=language)) == route
