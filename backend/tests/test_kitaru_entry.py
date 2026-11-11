"""Step 6: the worker entrypoint, with a fake worker environment and fake Kitaru."""

import json
import uuid
from types import SimpleNamespace

import pytest
from kitaru.api_models.v1.replay import ToolLookupMatch, ToolLookupResponse
from kitaru.api_models.v1.replay_config import (
    HistoryConfig,
    LLMConfig,
    PassthroughConfig,
    ReplayOverride,
    ToolPolicy,
)
from kitaru.api_models.v1.session_node import NodeStatus
from kitaru.api_models.v1.task import AgentTaskDetails
from kitaru.cache_keys import compute_tool_cache_key
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import func, select

import app.recording.recorder as rec
from app.agents.tutor import tutor_agent
from app.kitaru_entry import EXIT_BAD_REPLAY, EXIT_OK, EXIT_TURN_FAILED, question_and_history, run_task
from app.models import AgentRun, Message
from app.recording.recorder import turns_input
from tests.fakes import fake_agents
from tests.test_recording import FakeKitaru, FakeSessions

pytestmark = pytest.mark.anyio
TASK_ID = uuid.uuid4()
REPLAY_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def worker_env(monkeypatch):
    rec.reset_backoff()
    for name in ("KITARU_TASK_INPUTS", "KITARU_REPLAY_ID"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("KITARU_API_TOKEN", "task-token-SECRET-abcdef")
    yield
    rec.reset_backoff()


class FakeWorkerKitaru(FakeKitaru):
    """Adds the task spec, the replay, and history lookups to the fake."""

    def __init__(self, inputs, replay=None, recorded=None, **kw):
        super().__init__(**kw)
        self.spec_inputs = inputs
        self.replay = replay
        self.recorded = recorded or {}
        self.lookups = []
        self.clients = 0

    def client(self):
        self.clients += 1
        fake = self

        class Tasks:
            async def get_spec(self, task_id):
                assert task_id == TASK_ID
                return SimpleNamespace(
                    details=AgentTaskDetails(
                        kind="agent", inputs=fake.spec_inputs, replay_id=REPLAY_ID if fake.replay else None
                    )
                )

        class Replays:
            async def get(self, replay_id):
                assert replay_id == REPLAY_ID
                return fake.replay

            async def tool_lookup(self, replay_id, request):
                fake.lookups.append(request)
                return ToolLookupResponse(match=fake.recorded.get((request.cache_key, request.occurrence)))

        return SimpleNamespace(sessions=FakeSessions(fake), tasks=Tasks(), replays=Replays(), close=fake.close)


def replay(override=None, default=None, tools=None):
    return SimpleNamespace(
        id=REPLAY_ID,
        override=override,
        tool_policy=ToolPolicy(default=default or PassthroughConfig(), tools=tools or {}),
    )


def only_session(fake):
    assert len(fake.sessions) == 1
    return next(iter(fake.sessions.values()))


HISTORY = [("user", "Explain closures"), ("assistant", "A closure remembers...")]
RECORDED_INPUTS = turns_input("Another example?", HISTORY)


async def test_replay_reruns_the_recorded_turn(db):
    fake = FakeWorkerKitaru(RECORDED_INPUTS, replay=replay())
    seen = {}

    def tutor(messages, info):
        seen["messages"] = messages
        return ModelResponse(parts=[TextPart("new answer")])

    with fake_agents():
        with tutor_agent.override(model=FunctionModel(tutor)):
            code = await run_task(TASK_ID, fake.client)

    assert code == EXIT_OK
    s = only_session(fake)
    assert s["request"].origin.value == "replay"
    assert s["request"].inputs == RECORDED_INPUTS  # same inputs as the baseline
    assert s["request"].metadata["replay_id"] == str(REPLAY_ID)
    assert s["updates"][-1].outputs == {"answer": "new answer"}
    # The tutor saw the recorded history, then the recorded question.
    contents = [m.parts[0].content for m in seen["messages"]]
    assert contents == ["Explain closures", "A closure remembers...", "Another example?"]
    # Replays never write to the chat database.
    assert db.scalar(select(func.count()).select_from(Message)) == 0
    assert db.scalar(select(func.count()).select_from(AgentRun)) == 0
    assert fake.closed == fake.clients == 2  # task client + recorder client, both closed
    assert "task-token-SECRET-abcdef" not in repr(fake.sessions)


async def test_inputs_from_environment_take_priority(monkeypatch):
    monkeypatch.setenv("KITARU_TASK_INPUTS", json.dumps("Explain hoisting"))
    fake = FakeWorkerKitaru(inputs="ignored")
    with fake_agents(answer="ok"):
        assert await run_task(TASK_ID, fake.client) == EXIT_OK
    s = only_session(fake)
    assert s["request"].origin.value == "recorded"  # no replay id: a plain rerun
    assert s["request"].inputs == {"turns": [{"inputs": "Explain hoisting"}]}


async def test_history_policy_answers_tools_from_the_recording(monkeypatch):
    import app.tools.examples as examples

    monkeypatch.setattr(examples, "load_examples", lambda: (_ for _ in ()).throw(AssertionError("live tool ran")))
    key = compute_tool_cache_key("get_code_example", {"topic": "closures"})
    fake = FakeWorkerKitaru(
        RECORDED_INPUTS,
        replay=replay(default=HistoryConfig(scope="baseline", on_miss="fail")),
        recorded={(key, 0): ToolLookupMatch(result={"code": "recorded!"}, status=NodeStatus.COMPLETED)},
    )
    with fake_agents(tool_calls=[("get_code_example", {"topic": "closures"})], answer="done"):
        assert await run_task(TASK_ID, fake.client) == EXIT_OK
    assert fake.lookups[0].occurrence == 0
    tool = next(n for n in only_session(fake)["nodes"].values() if n.node_type.value == "tool_call")
    assert tool.outputs == {"code": "recorded!"} and tool.attributes["mocked"] is True


async def test_unsupported_replay_is_rejected_before_anything_runs():
    fake = FakeWorkerKitaru(RECORDED_INPUTS, replay=replay(default=LLMConfig(model="gpt-4o-mini")))

    def must_not_run(messages, info):
        raise AssertionError("model called for a rejected replay")

    with tutor_agent.override(model=FunctionModel(must_not_run)):
        assert await run_task(TASK_ID, fake.client) == EXIT_BAD_REPLAY
    assert fake.sessions == {}  # no session created


async def test_bad_inputs_are_rejected():
    fake = FakeWorkerKitaru({"something": "else"})
    assert await run_task(TASK_ID, fake.client) == EXIT_BAD_REPLAY
    assert fake.sessions == {}


async def test_no_session_no_spending():
    fake = FakeWorkerKitaru(RECORDED_INPUTS, replay=replay(), fail={"create"})

    def must_not_run(messages, info):
        raise AssertionError("model called without a session")

    with tutor_agent.override(model=FunctionModel(must_not_run)):
        assert await run_task(TASK_ID, fake.client) == EXIT_TURN_FAILED


async def test_failed_turn_fails_the_task_and_the_session():
    fake = FakeWorkerKitaru(RECORDED_INPUTS, replay=replay())

    def broken(messages, info):
        raise RuntimeError("tutor down")

    with fake_agents():
        with tutor_agent.override(model=FunctionModel(broken)):
            assert await run_task(TASK_ID, fake.client) == EXIT_TURN_FAILED
    s = only_session(fake)
    assert s["updates"][-1].status.value == "failed" and "tutor down" in s["updates"][-1].error


async def test_incomplete_recording_fails_the_task():
    fake = FakeWorkerKitaru(RECORDED_INPUTS, replay=replay(), fail={"nodes"})
    with fake_agents(answer="ok"):
        assert await run_task(TASK_ID, fake.client) == EXIT_TURN_FAILED


async def test_override_prompt_and_model_reach_the_run(monkeypatch):
    swapped = FunctionModel(lambda m, i: ModelResponse(parts=[TextPart("from gpt-4.1-mini")]), model_name="gpt-4.1-mini")
    monkeypatch.setattr("app.agents.models.chat_model_named", lambda name: swapped)
    fake = FakeWorkerKitaru(
        RECORDED_INPUTS,
        # Map only the tutor's model; the classifier's model (named "test") is left alone.
        replay=replay(override=ReplayOverride(prompt="Explain closures simply", model={"gpt-4o-mini": "gpt-4.1-mini"})),
    )
    original = FunctionModel(lambda m, i: ModelResponse(parts=[TextPart("from original")]), model_name="gpt-4o-mini")
    with fake_agents():
        with tutor_agent.override(model=original):
            assert await run_task(TASK_ID, fake.client) == EXIT_OK
    s = only_session(fake)
    assert s["updates"][-1].outputs == {"answer": "from gpt-4.1-mini"}
    classify = next(n for n in s["nodes"].values() if n.name == "classify")
    assert classify.inputs == {"question": "Explain closures simply"}
    tutor_call = next(n for n in s["nodes"].values() if n.name == "tutor.model_request")
    assert tutor_call.requested_model == "gpt-4o-mini" and tutor_call.attributes["override"] == {"model": "gpt-4.1-mini"}
    classifier_call = next(n for n in s["nodes"].values() if n.name == "classifier.model_request")
    assert "override" not in classifier_call.attributes


def test_question_and_history_formats():
    assert question_and_history("plain question") == ("plain question", [])
    assert question_and_history(RECORDED_INPUTS) == ("Another example?", HISTORY)
    with pytest.raises(ValueError):
        question_and_history({"turns": []})
