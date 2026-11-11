"""The tutor turn + persistence through the orchestration function (agent faked)."""

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.agents.prompts import TUTOR_SYSTEM_PROMPT
from app.agents.tutor import tutor_agent
from app.agents.workflow import WorkflowError, run_chat_turn
from app.models import AgentRun, Conversation, Message, TeamMember
from tests.fakes import fake_agents

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


async def test_every_message_goes_to_the_tutor_with_its_full_prompt(db, conversation):
    seen = {}

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["instructions"] = info.instructions
        return ModelResponse(parts=[TextPart("ok")])

    # No classifier: even an off-topic question reaches the tutor, which decides scope itself.
    with tutor_agent.override(model=FunctionModel(respond)):
        result = await run_chat_turn(db, conversation, "Best tacos in Austin?")

    assert result.response == "ok"
    assert seen["instructions"].strip() == TUTOR_SYSTEM_PROMPT.strip()
    assert "### Scope" in seen["instructions"] and "### Task Rules" in seen["instructions"]
    assert "Current task:" not in seen["instructions"]


async def test_turn_persists_messages_run_log_and_title(db, conversation, ingested_lessons):
    with fake_agents(tool_calls=[("search_lessons", {"query": "closures"})], answer="Closures remember."):
        result = await run_chat_turn(db, conversation, "Explain JavaScript closures")

    messages = db.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)).all()
    assert [(m.role, m.content) for m in messages] == [
        ("user", "Explain JavaScript closures"),
        ("assistant", "Closures remember."),
    ]
    run = db.scalar(select(AgentRun).where(AgentRun.request_id == result.request_id))
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

    with tutor_agent.override(model=FunctionModel(respond)):
        await run_chat_turn(db, conversation, "Show another example")

    assert seen["first"] == "Explain closures"
    assert seen["count"] == 3  # previous user msg, previous answer, new question


async def test_failure_is_logged_and_raised(db, conversation):
    def broken(messages, info):
        raise RuntimeError("model exploded")

    with tutor_agent.override(model=FunctionModel(broken)):
        with pytest.raises(WorkflowError) as exc_info:
            await run_chat_turn(db, conversation, "Explain closures")

    run = db.scalar(select(AgentRun).where(AgentRun.request_id == exc_info.value.request_id))
    assert "model exploded" in run.error_message
    roles = db.scalars(select(Message.role).where(Message.conversation_id == conversation.id)).all()
    assert roles == ["user"]  # question kept, no assistant message
