"""Routing + persistence through the orchestration function (agents faked)."""

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.agents.prompts import OTHER_LANGUAGE_RESPONSE, OUT_OF_SCOPE_RESPONSE, TUTOR_SYSTEM_PROMPT
from app.agents.tutor import tutor_agent
from app.agents.workflow import WorkflowError, run_chat_turn
from app.models import AgentRun, Conversation, Message, TeamMember
from tests.fakes import fake_agents, fake_classifier_model
from app.agents.classifier import classifier_agent

pytestmark = pytest.mark.anyio


@pytest.fixture
def conversation(db):
    member = TeamMember(display_name="Tester")
    db.add(member)
    db.commit()
    conv = Conversation(team_member_id=member.id)
    db.add(conv)
    db.commit()
    return conv


async def test_out_of_scope_skips_tutor_and_rag(db, conversation):
    def tutor_must_not_run(messages, info):
        raise AssertionError("tutor should not be called for out-of-scope questions")

    with (
        classifier_agent.override(model=fake_classifier_model("out_of_scope", "concept", "unknown")),
        tutor_agent.override(model=FunctionModel(tutor_must_not_run)),
    ):
        result = await run_chat_turn(db, conversation, "Best tacos in Austin?")

    assert result.route == "out_of_scope"
    assert result.response == OUT_OF_SCOPE_RESPONSE
    assert result.tools_called == [] and result.sources == []


async def test_other_language_gets_javascript_redirect(db, conversation):
    with fake_agents(classification=("out_of_scope", "concept", "other")):
        result = await run_chat_turn(db, conversation, "How do decorators work in Python?")
    assert result.route == "out_of_scope_other_language"
    assert result.response == OTHER_LANGUAGE_RESPONSE


@pytest.mark.parametrize("intent", ["concept", "debugging", "code_generation", "quiz"])
async def test_in_scope_routes_to_tutor_with_route_instructions(db, conversation, intent):
    seen = {}

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["instructions"] = info.instructions
        return ModelResponse(parts=[TextPart("ok")])

    with (
        classifier_agent.override(model=fake_classifier_model("in_scope", intent, "javascript")),
        tutor_agent.override(model=FunctionModel(respond)),
    ):
        result = await run_chat_turn(db, conversation, "question")

    assert result.route == intent
    assert result.response == "ok"
    # One big prompt with every task's rules, then a one-line label for this route.
    assert seen["instructions"].startswith(TUTOR_SYSTEM_PROMPT.strip()[:40])
    assert "### Task Rules" in seen["instructions"]
    assert seen["instructions"].rstrip().endswith(f"Current task: {intent}")


async def test_turn_persists_messages_run_log_and_title(db, conversation, ingested_lessons):
    with fake_agents(tool_calls=[("search_lessons", {"query": "closures"})], answer="Closures remember."):
        result = await run_chat_turn(db, conversation, "Explain JavaScript closures")

    messages = db.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)).all()
    assert [(m.role, m.content) for m in messages] == [
        ("user", "Explain JavaScript closures"),
        ("assistant", "Closures remember."),
    ]
    run = db.scalar(select(AgentRun).where(AgentRun.request_id == result.request_id))
    assert run.scope == "in_scope" and run.intent == "concept" and run.selected_route == "concept"
    assert run.tools_called == ["search_lessons"]
    assert any(s["source_filename"] == "04-javascript-closures.md" for s in run.retrieved_sources)
    assert run.message_id == messages[1].id
    assert run.model_name == "gpt-4o-mini"
    assert run.error_message is None
    db.refresh(conversation)
    assert conversation.title == "Explain JavaScript closures"


async def test_follow_up_sends_recent_history_to_tutor(db, conversation):
    with fake_agents(answer="first answer"):
        await run_chat_turn(db, conversation, "Explain closures")

    seen = {}

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["count"] = len(messages)
        seen["first"] = messages[0].parts[0].content
        return ModelResponse(parts=[TextPart("second answer")])

    with (
        classifier_agent.override(model=fake_classifier_model("in_scope", "concept", "javascript")),
        tutor_agent.override(model=FunctionModel(respond)),
    ):
        await run_chat_turn(db, conversation, "Show another example")

    assert seen["first"] == "Explain closures"
    assert seen["count"] == 3  # previous user msg, previous answer, new question


async def test_failure_is_logged_and_raised(db, conversation):
    def broken(messages, info):
        raise RuntimeError("model exploded")

    with (
        classifier_agent.override(model=fake_classifier_model("in_scope", "concept", "javascript")),
        tutor_agent.override(model=FunctionModel(broken)),
    ):
        with pytest.raises(WorkflowError) as exc_info:
            await run_chat_turn(db, conversation, "Explain closures")

    run = db.scalar(select(AgentRun).where(AgentRun.request_id == exc_info.value.request_id))
    assert "model exploded" in run.error_message
    assert run.selected_route == "concept"
    roles = db.scalars(select(Message.role).where(Message.conversation_id == conversation.id)).all()
    assert roles == ["user"]  # question kept, no assistant message
