"""RAG retrieval shows up in the trace like OpenInference: tool -> RETRIEVER span -> EMBEDDING call."""

from types import SimpleNamespace

import pytest
from kitaru.api_models.v1.replay_config import HistoryConfig, ToolPolicy
from kitaru.api_models.v1.replay import ToolLookupMatch, ToolLookupResponse
from kitaru.api_models.v1.session_node import NodeStatus
from kitaru.cache_keys import compute_tool_cache_key

import app.rag.retrieve as retrieve
import app.recording.recorder as rec
from app.agents.deps import TutorDeps
from app.agents.tutor import tutor_agent
from app.recording.hooks import RecordingHooks
from app.recording.replay import ReplayPlan
from tests.conftest import fake_embed_texts
from tests.fakes import scripted_tutor_model
from tests.test_recording import FakeKitaru, node_named, only_session, recorder_for

pytestmark = pytest.mark.anyio
REAL_EMBED_TEXTS = retrieve.embed_texts  # captured before conftest swaps it for a fake


class FakeOpenAI:
    """Just enough of the OpenAI client for embeddings.create."""

    def __init__(self, fail=False):
        self.fail = fail
        self.embeddings = self

    def create(self, model, input, dimensions):
        if self.fail:
            raise ConnectionError("OpenAI embeddings unreachable")
        vectors = fake_embed_texts(input)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=v) for v in vectors],
            model=model,
            usage=SimpleNamespace(prompt_tokens=7),
        )


@pytest.fixture(autouse=True)
def real_embedding_code(monkeypatch):
    """Run the real embed_texts (so it can record itself) against a fake OpenAI client."""
    rec.reset_backoff()
    fake = FakeOpenAI()
    monkeypatch.setattr(retrieve, "embed_texts", REAL_EMBED_TEXTS)
    monkeypatch.setattr(retrieve, "_openai_client", lambda: fake)
    yield fake
    rec.reset_backoff()


async def run_tutor_with_search(recorder, queries, replay=None):
    span = recorder.begin_span("invoke_agent tutor")
    tool_calls = [("search_lessons", {"query": q}) for q in queries]
    with tutor_agent.override(model=scripted_tutor_model(tool_calls, "done")):
        await tutor_agent.run(
            "q", deps=TutorDeps(route="concept"), capabilities=[RecordingHooks(recorder, span, "tutor", replay=replay)]
        )
    recorder.end_span(span)


async def test_retrieval_is_nested_under_the_tool(ingested_lessons):
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    await run_tutor_with_search(recorder, ["closures counter private state"])
    await recorder.finish(answer="done")

    s = only_session(fake)
    tool = node_named(s, "execute_tool search_lessons")
    retriever = node_named(s, "retrieve lessons")
    embedding = node_named(s, "embeddings text-embedding-3-small")
    assert retriever.parent_external_id == tool.external_id
    assert embedding.parent_external_id == retriever.external_id

    # RETRIEVER span: query in, document ids + scores out (full text lives in the tool output).
    assert retriever.node_type.value == "span"
    assert retriever.attributes["openinference.span.kind"] == "RETRIEVER"
    assert retriever.attributes["db.system.name"] == "postgresql"
    assert retriever.inputs == {"query": "closures counter private state", "top_k": 3}
    docs = retriever.outputs["documents"]
    assert len(docs) == 3 and docs[0]["source_filename"] == "04-javascript-closures.md"
    assert set(docs[0]) == {"id", "title", "source_filename", "score"}

    # EMBEDDING call: model, tokens, size; never the vector itself.
    assert embedding.node_type.value == "llm_call"
    assert embedding.attributes["gen_ai.operation.name"] == "embeddings"
    assert embedding.model == "text-embedding-3-small" and embedding.tokens.input_tokens == 7
    assert embedding.outputs == {"embeddings": 1, "dimensions": 1536}
    assert embedding.inputs == {"input": ["closures counter private state"]}
    assert len(repr(s["nodes"])) < 200_000  # no 1536-number vectors in the trace


async def test_parallel_searches_each_get_their_own_retrieval(ingested_lessons):
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    await run_tutor_with_search(recorder, ["closures", "promises"])  # two tool calls in one model step
    await recorder.finish(answer="done")

    nodes = list(only_session(fake)["nodes"].values())
    tools = [n for n in nodes if n.name == "execute_tool search_lessons"]
    retrievers = [n for n in nodes if n.name == "retrieve lessons"]
    assert len(tools) == 2 and len(retrievers) == 2
    by_tool = {r.parent_external_id: r.inputs["query"] for r in retrievers}
    assert {by_tool[t.external_id] for t in tools} == {t.inputs["query"] for t in tools}  # each under its own call


async def test_failed_retrieval_is_visible_even_though_the_tool_recovers(ingested_lessons, real_embedding_code):
    real_embedding_code.fail = True
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    await run_tutor_with_search(recorder, ["closures"])
    await recorder.finish(answer="done")

    s = only_session(fake)
    # search_lessons catches the error and returns [], so the tool call itself succeeds...
    tool = node_named(s, "execute_tool search_lessons")
    assert tool.status == NodeStatus.COMPLETED and tool.outputs == []
    # ...but the trace shows exactly which step failed.
    assert node_named(s, "retrieve lessons").status == NodeStatus.FAILED
    embedding = node_named(s, "embeddings text-embedding-3-small")
    assert embedding.status == NodeStatus.FAILED and "unreachable" in embedding.error


async def test_history_replay_skips_retrieval():
    key = compute_tool_cache_key("search_lessons", {"query": "closures"})

    async def lookup(tool_name, cache_key, occurrence):
        return ToolLookupResponse(match=ToolLookupMatch(result=[], status=NodeStatus.COMPLETED) if cache_key == key else None)

    plan = ReplayPlan(None, ToolPolicy(default=HistoryConfig(scope="baseline", on_miss="fail"), tools={}), lookup)
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    await run_tutor_with_search(recorder, ["closures"], replay=plan)
    await recorder.finish(answer="done")

    names = {n.name for n in only_session(fake)["nodes"].values()}
    assert "execute_tool search_lessons" in names
    assert "retrieve lessons" not in names  # nothing was fetched, so nothing is shown


def test_retrieval_outside_a_turn_records_nothing(db, ingested_lessons):
    results = retrieve.search_chunks(db, "closures")  # e.g. scripts and tests: no recorder active
    assert len(results) == 3
