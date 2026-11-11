"""Step 4: answer_turn (no DB writes) + run_chat_turn recording a whole turn as one session."""

import uuid

import pytest
from kitaru.api_models.v1.replay_config import PassthroughConfig, ReplayOverride, ToolPolicy
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import func, select

import app.agents.workflow as workflow
import app.recording.recorder as rec
from app.agents.prompts import TUTOR_SYSTEM_PROMPT
from app.agents.tutor import tutor_agent
from app.agents.workflow import TurnFailed, WorkflowError, answer_turn, run_chat_turn
from app.models import AgentRun, Conversation, Message, TeamMember
from app.recording.replay import ReplayPlan
from tests.fakes import fake_agents
from tests.test_recording import FakeKitaru, node_named, only_session, recorder_for

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def no_backoff():
    rec.reset_backoff()
    yield
    rec.reset_backoff()


@pytest.fixture
def conversation(db):
    member = TeamMember(display_name="Tester")
    db.add(member)
    db.commit()
    conv = Conversation(team_member_id=member.id)
    db.add(conv)
    db.commit()
    return conv


@pytest.fixture
def recording_on(monkeypatch):
    """Turn recording on for run_chat_turn, into a fake Kitaru."""
    fake = FakeKitaru()
    agent_id = uuid.uuid4()
    monkeypatch.setattr(workflow, "new_turn_recorder", lambda: recorder_for(fake, secrets=[]))
    monkeypatch.setattr(workflow, "agent_ids", lambda: (agent_id, None))
    fake.agent_id = agent_id
    return fake


def names(session):
    return [n.name for n in session["nodes"].values()]


def replay_plan(**override):
    return ReplayPlan(
        override=ReplayOverride(**override),
        tool_policy=ToolPolicy(default=PassthroughConfig(), tools={}),
        lookup=None,
    )


# ---------- answer_turn ----------


async def test_answer_turn_writes_nothing_to_the_database(db):
    before = db.scalar(select(func.count()).select_from(Message))
    with fake_agents(answer="hi"):
        answer = await answer_turn("Explain closures", [])
    assert answer.response == "hi"
    assert db.scalar(select(func.count()).select_from(Message)) == before
    assert db.scalar(select(func.count()).select_from(AgentRun)) == 0


async def test_answer_turn_records_the_agreed_tree():
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="Explain closures", history=[])
    with fake_agents(tool_calls=[("get_code_example", {"topic": "closures"})], answer="Closures!"):
        answer = await answer_turn("Explain closures", [], recorder=recorder)
    await recorder.finish(answer=answer.response)

    s = only_session(fake)
    by_id = s["nodes"]
    def label(n):  # model-call names include the model; label them by agent instead
        if n.node_type.value == "llm_call":
            return f"chat by {n.attributes['gen_ai.agent.name']}"
        return n.name

    parent_label = lambda n: label(by_id[n.parent_external_id]) if n.parent_external_id else "-"  # noqa: E731
    tree = sorted((parent_label(n), label(n)) for n in by_id.values())
    assert tree == sorted(
        [
            ("-", "invoke_agent studybot"),
            ("invoke_agent studybot", "invoke_agent tutor"),
            ("invoke_agent tutor", "chat by tutor"),
            ("invoke_agent tutor", "execute_tool get_code_example"),
            ("invoke_agent tutor", "chat by tutor"),
        ]
    )
    tutor = node_named(s, "invoke_agent tutor")
    assert tutor.attributes == {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "tutor"}
    assert tutor.inputs == {"question": "Explain closures"}
    assert tutor.outputs == {"answer": "Closures!"}


async def test_prompt_override_changes_the_question():
    seen = {}

    def tutor(messages, info: AgentInfo):
        seen["tutor"] = messages[-1].parts[-1].content
        return ModelResponse(parts=[TextPart("ok")])

    with tutor_agent.override(model=FunctionModel(tutor)):
        answer = await answer_turn("original question", [], replay=replay_plan(prompt="NEW question"))
    assert seen["tutor"] == "NEW question"
    assert answer.question == "NEW question"


async def test_system_prompt_override_replaces_the_whole_tutor_prompt():
    seen = {}

    def tutor(messages, info: AgentInfo):
        seen["tutor"] = info.instructions
        return ModelResponse(parts=[TextPart("ok")])

    with tutor_agent.override(model=FunctionModel(tutor)):
        await answer_turn("Quiz me", [], replay=replay_plan(system_prompt="BE VERY BRIEF."))
    assert seen["tutor"] == "BE VERY BRIEF."  # nothing else is appended
    with tutor_agent.override(model=FunctionModel(tutor)):
        await answer_turn("Quiz me", [])
    assert seen["tutor"].strip() == TUTOR_SYSTEM_PROMPT.strip()  # the override did not stick


async def test_failure_reports_how_far_the_turn_got():
    def broken(messages, info):
        raise RuntimeError("tutor down")

    with tutor_agent.override(model=FunctionModel(broken)):
        with pytest.raises(TurnFailed) as exc_info:
            await answer_turn("why undefined?", [])
    assert exc_info.value.partial.question == "why undefined?"
    assert exc_info.value.partial.response is None
    assert isinstance(exc_info.value.__cause__, RuntimeError)


# ---------- run_chat_turn: live recording ----------


async def test_live_turn_is_recorded_as_one_session(db, conversation, recording_on):
    with fake_agents(answer="first"):
        await run_chat_turn(db, conversation, "Explain closures")
    with fake_agents(answer="second"):
        result = await run_chat_turn(db, conversation, "Another example?")

    assert result.response == "second"
    assert len(recording_on.sessions) == 2  # one session per turn
    second = next(s for s in recording_on.sessions.values() if s["request"].metadata["request_id"] == str(result.request_id))
    assert second["request"].agent_id == recording_on.agent_id
    assert second["request"].metadata["conversation_id"] == str(conversation.id)
    # The history the app used is in the session inputs.
    assert second["request"].inputs == {
        "turns": [{"inputs": "Explain closures", "outputs": "first"}, {"inputs": "Another example?"}]
    }
    assert second["updates"][-1].status.value == "completed"
    assert second["updates"][-1].outputs == {"answer": "second"}
    # Loading that history is its own step.
    load = next(n for n in second["nodes"].values() if n.name == "load history")
    assert load.parent_external_id == next(n for n in second["nodes"].values() if n.parent_external_id is None).external_id
    assert load.inputs["conversation_id"] == str(conversation.id)
    assert load.outputs == {"messages": 2, "roles": ["user", "assistant"]}
    assert load.attributes["db.collection.name"] == "messages"


async def test_chat_still_works_when_kitaru_is_down(db, conversation, monkeypatch):
    fake = FakeKitaru(fail={"create"})
    monkeypatch.setattr(workflow, "new_turn_recorder", lambda: recorder_for(fake, secrets=[]))
    monkeypatch.setattr(workflow, "agent_ids", lambda: (uuid.uuid4(), None))
    with fake_agents(answer="still answering"):
        result = await run_chat_turn(db, conversation, "Explain closures")
    assert result.response == "still answering"
    assert fake.sessions == {}


async def test_failed_live_turn_records_failed_session(db, conversation, recording_on):
    def broken(messages, info):
        raise RuntimeError("tutor down")

    with tutor_agent.override(model=FunctionModel(broken)):
        with pytest.raises(WorkflowError):
            await run_chat_turn(db, conversation, "Explain closures")

    s = only_session(recording_on)
    assert s["updates"][-1].status.value == "failed"
    assert "tutor down" in s["updates"][-1].error
    tutor_span = node_named(s, "invoke_agent tutor")
    assert tutor_span.status.value == "failed"
    run = db.scalar(select(AgentRun))
    assert "tutor down" in run.error_message


# ---------- Step 5: outcome is stored and shown ----------


async def test_outcome_is_stored_on_agent_runs(db, conversation, recording_on):
    with fake_agents(answer="ok"):
        result = await run_chat_turn(db, conversation, "Explain closures")
    run = db.scalar(select(AgentRun).where(AgentRun.request_id == result.request_id))
    assert run.kitaru_status == result.kitaru_status == "recorded"
    assert run.kitaru_session_id == result.kitaru_session_id == only_session_id(recording_on)
    assert run.kitaru_problem is None


async def test_unrecorded_outcome_keeps_the_problem(db, conversation, monkeypatch):
    fake = FakeKitaru(fail={"create"})
    monkeypatch.setattr(workflow, "new_turn_recorder", lambda: recorder_for(fake, secrets=[]))
    monkeypatch.setattr(workflow, "agent_ids", lambda: (uuid.uuid4(), None))
    with fake_agents(answer="ok"):
        result = await run_chat_turn(db, conversation, "Explain closures")
    run = db.scalar(select(AgentRun).where(AgentRun.request_id == result.request_id))
    assert run.kitaru_status == "unrecorded" and run.kitaru_session_id is None
    assert run.kitaru_problem.startswith("create session")


async def test_recording_off_by_default(db, conversation):
    with fake_agents(answer="ok"):
        result = await run_chat_turn(db, conversation, "Explain closures")
    assert result.kitaru_status == "disabled"


def only_session_id(fake):
    assert len(fake.sessions) == 1
    return next(iter(fake.sessions))


def test_init_db_adds_new_columns_to_an_existing_table():
    from sqlalchemy import inspect, text

    from app.database import create_tables, get_engine

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE agent_runs DROP COLUMN kitaru_problem"))
    create_tables()
    create_tables()  # safe to run twice
    columns = {c["name"] for c in inspect(engine).get_columns("agent_runs")}
    assert {"kitaru_status", "kitaru_session_id", "kitaru_problem"} <= columns
