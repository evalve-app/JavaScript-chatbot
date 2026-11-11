"""Recorder core: lifecycle, best-effort failures, privacy. Fake Kitaru client, no network."""

import asyncio
import uuid

import pytest
from kitaru.api_models.v1.session import SessionOrigin
from kitaru.api_models.v1.session_node import NodeType

import app.recording.recorder as rec
from app.config import Settings
from app.recording.capture import MAX_STRING, REDACTED, capture, secret_values
from app.recording.recorder import Outcome, TurnRecorder, history_from_turns, turns_input

SENTINEL = "sk-sentinel-SECRET-123456"
pytestmark = pytest.mark.anyio


class FakeSession:
    def __init__(self, id):
        self.id = id


class FakeSessions:
    def __init__(self, kitaru):
        self.k = kitaru

    async def _maybe_fail(self, op):
        self.k.calls.append(op)
        if self.k.hang == op:
            await asyncio.sleep(10)
        if op in self.k.fail:
            raise ConnectionError(f"{op} failed (token {SENTINEL})")

    async def create(self, request):
        await self._maybe_fail("create")
        session_id = uuid.uuid4()
        self.k.sessions[session_id] = {"request": request, "updates": [], "nodes": {}}
        return FakeSession(session_id)

    async def ingest_nodes(self, session_id, batch):
        op = "root" if [n.external_id for n in batch.nodes] == [rec.ROOT_ID] else "nodes"
        await self._maybe_fail(op)
        for node in batch.nodes:
            nodes = self.k.sessions[session_id]["nodes"]
            if node.parent_external_id is not None:
                assert node.parent_external_id in nodes, "parent must be written before child"
            nodes[node.external_id] = node  # same id replaces (root transition)
        return []

    async def update(self, session_id, request):
        await self._maybe_fail("update")
        self.k.sessions[session_id]["updates"].append(request)


class FakeKitaru:
    def __init__(self, fail=(), hang=None):
        self.fail = set(fail)
        self.hang = hang
        self.calls: list[str] = []
        self.sessions: dict = {}
        self.closed = 0
        self.sessions_api = FakeSessions(self)

    async def close(self):
        self.closed += 1


class ClientView:
    """What the recorder sees: client.sessions.<method>, client.close()."""

    def __init__(self, fake):
        self.sessions = fake.sessions_api
        self.close = fake.close


@pytest.fixture(autouse=True)
def no_backoff():
    rec.reset_backoff()
    yield
    rec.reset_backoff()


def recorder_for(fake, secrets=(SENTINEL,)):
    return TurnRecorder(lambda: ClientView(fake), list(secrets))


async def record_simple_turn(recorder, error=None):
    await recorder.start(question="Explain closures", history=[("user", "hi"), ("assistant", "hello")])
    span = recorder.add_node(node_type=NodeType.SPAN, name="classify", outputs={"route": "concept"})
    recorder.add_node(node_type=NodeType.LLM_CALL, name="classifier", parent=span, inputs={"prompt": "x"})
    return await recorder.finish(answer=None if error else "A closure is...", error=error)


def llm_calls(session, agent):
    """Model calls made by one agent (names include the model, so match on the agent)."""
    return [
        n
        for n in session["nodes"].values()
        if n.node_type.value == "llm_call" and n.attributes.get("gen_ai.agent.name") == agent
    ]


def node_named(session, name):
    return next(n for n in session["nodes"].values() if n.name == name)


def only_session(fake):
    assert len(fake.sessions) == 1
    return next(iter(fake.sessions.values()))


# ---------- happy path ----------


async def test_records_session_root_and_children():
    fake = FakeKitaru()
    outcome = await record_simple_turn(recorder_for(fake))

    assert outcome == Outcome.RECORDED
    s = only_session(fake)
    assert s["request"].origin == SessionOrigin.RECORDED
    assert s["request"].status.value == "in_progress"
    assert s["request"].inputs == {
        "turns": [{"inputs": "hi", "outputs": "hello"}, {"inputs": "Explain closures"}]
    }
    assert s["request"].input_text_selector == "/turns/1/inputs"
    root = s["nodes"][rec.ROOT_ID]
    assert root.status.value == "completed" and root.outputs == {"answer": "A closure is..."}
    names = {n.name: n for n in s["nodes"].values()}
    assert names["classifier"].parent_external_id == names["classify"].external_id
    assert names["classify"].parent_external_id == rec.ROOT_ID
    assert s["updates"][-1].status.value == "completed"
    assert fake.closed == 1


async def test_app_failure_is_recorded_as_failed_session():
    fake = FakeKitaru()
    outcome = await record_simple_turn(recorder_for(fake), error=RuntimeError("tutor crashed"))
    s = only_session(fake)
    assert outcome == Outcome.RECORDED  # the failure itself was fully recorded
    assert s["nodes"][rec.ROOT_ID].status.value == "failed"
    assert "tutor crashed" in s["updates"][-1].error
    assert s["updates"][-1].status.value == "failed"


async def test_disabled_recorder_does_nothing():
    recorder = TurnRecorder(None, [])
    await recorder.start(question="q", history=[])
    node_id = recorder.add_node(node_type=NodeType.SPAN, name="x")
    assert node_id  # callers can still use ids without branching
    assert await recorder.finish(answer="a") == Outcome.DISABLED


# ---------- best effort: every failure point ----------


async def test_create_failure_leaves_turn_unrecorded_and_starts_backoff():
    fake = FakeKitaru(fail={"create"})
    recorder = recorder_for(fake)
    assert await record_simple_turn(recorder) == Outcome.UNRECORDED
    assert recorder.problem.startswith("create session")
    assert fake.closed == 1

    # The next turn within the backoff window doesn't even try.
    fake2 = FakeKitaru()
    second = recorder_for(fake2)
    assert await record_simple_turn(second) == Outcome.UNRECORDED
    assert fake2.calls == [] and "skipped" in second.problem


async def test_root_failure_marks_session_failed_and_partial():
    fake = FakeKitaru(fail={"root"})
    recorder = recorder_for(fake)
    assert await record_simple_turn(recorder) == Outcome.PARTIAL
    s = only_session(fake)
    assert s["updates"][-1].status.value == "failed"
    assert fake.closed == 1


async def test_child_ingest_failure_is_partial_not_complete():
    fake = FakeKitaru(fail={"nodes"})
    recorder = recorder_for(fake)
    assert await record_simple_turn(recorder) == Outcome.PARTIAL
    s = only_session(fake)
    assert s["nodes"][rec.ROOT_ID].status.value == "in_progress"  # never claimed complete
    assert s["updates"][-1].status.value == "failed"
    assert "0 child nodes stored" in s["updates"][-1].error


async def test_final_update_failure_is_partial():
    fake = FakeKitaru(fail={"update"})
    recorder = recorder_for(fake)
    assert await record_simple_turn(recorder) == Outcome.PARTIAL
    assert recorder.problem.startswith("finish")


async def test_slow_kitaru_times_out_instead_of_blocking(monkeypatch):
    monkeypatch.setattr(rec, "WRITE_TIMEOUT_SECONDS", 0.05)
    fake = FakeKitaru(hang="create")
    recorder = recorder_for(fake)
    assert await asyncio.wait_for(record_simple_turn(recorder), 2) == Outcome.UNRECORDED
    assert "TimeoutError" in recorder.problem


async def test_client_factory_failure_is_unrecorded():
    def broken_factory():
        raise RuntimeError("no Kitaru URL configured")

    recorder = TurnRecorder(broken_factory, [])
    assert await record_simple_turn(recorder) == Outcome.UNRECORDED


async def test_concurrent_turns_stay_separate():
    fake = FakeKitaru()

    async def turn(question, delay):
        r = recorder_for(fake)
        await r.start(question=question, history=[])
        await asyncio.sleep(delay)
        r.add_node(node_type=NodeType.SPAN, name=f"span-{question}")
        await r.finish(answer=f"answer-{question}")
        return r.session_id

    a, b = await asyncio.gather(turn("A", 0.02), turn("B", 0))
    assert a != b
    for sid, q in [(a, "A"), (b, "B")]:
        names = {n.name for n in fake.sessions[sid]["nodes"].values()}
        assert names == {"invoke_agent studybot", f"span-{q}"}
        assert fake.sessions[sid]["nodes"][rec.ROOT_ID].outputs == {"answer": f"answer-{q}"}


# ---------- privacy and bounds ----------


async def test_secrets_never_reach_kitaru():
    fake = FakeKitaru()
    recorder = recorder_for(fake)
    await recorder.start(question=f"my key is {SENTINEL}", history=[("assistant", SENTINEL)])
    recorder.add_node(
        node_type=NodeType.TOOL_CALL,
        name="search_lessons",
        inputs={"query": SENTINEL, "nested": [{"x": SENTINEL}]},
        error=ValueError(f"boom {SENTINEL}"),
        attributes={"note": SENTINEL},
    )
    await recorder.finish(error=RuntimeError(f"failed with {SENTINEL}"))
    stored = repr(fake.sessions)
    assert SENTINEL not in stored
    assert REDACTED in stored


async def test_kitaru_error_text_is_redacted_in_problem():
    fake = FakeKitaru(fail={"create"})
    recorder = recorder_for(fake)
    await record_simple_turn(recorder)
    assert SENTINEL not in recorder.problem


def test_secret_values_include_database_password():
    settings = Settings(
        openai_api_key="sk-real-key-abcdef",
        database_url="postgresql+psycopg://user:db-password-xyz@host/db",
        _env_file=None,
    )
    secrets = secret_values(settings)
    assert "sk-real-key-abcdef" in secrets and "db-password-xyz" in secrets
    url = "postgresql+psycopg://user:db-password-xyz@host/db"
    assert capture(f"url={url}", secrets) == f"url={REDACTED}"


def test_capture_bounds_and_unknown_objects():
    long = "x" * (MAX_STRING + 50)
    assert capture(long, []).endswith("[truncated 50 chars]")
    nested: dict = {}
    cur = nested
    for _ in range(20):
        cur["a"] = {}
        cur = cur["a"]
    assert "[max depth reached]" in repr(capture(nested, []))
    assert capture(object(), []) == "[unrecordable object]"
    assert len(capture(list(range(500)), [])) == 201


# ---------- input format ----------


@pytest.mark.parametrize(
    "history",
    [
        [],
        [("user", "q1"), ("assistant", "a1")],
        [("user", "q1"), ("user", "q2"), ("assistant", "a2")],  # a failed turn left q1 unanswered
        [("assistant", "a0"), ("user", "q1"), ("assistant", "a1")],  # history cut mid-exchange
    ],
)
def test_turns_input_round_trips(history):
    assert history_from_turns(turns_input("now?", history)) == ("now?", history)


def test_history_from_turns_rejects_bad_input():
    with pytest.raises(ValueError):
        history_from_turns({"turns": []})
