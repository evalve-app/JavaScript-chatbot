import json

import pytest
from pydantic_ai.models.test import TestModel

from app.agents.deps import TutorDeps
from app.agents.tutor import tutor_agent
from app.tools.examples import get_code_example, load_examples
from app.tools.progress import get_mock_progress
from app.tools.search import search_lessons


class FakeCtx:
    def __init__(self):
        self.deps = TutorDeps(route="concept")


def test_tools_are_registered_with_stable_names():
    assert set(tutor_agent._function_toolset.tools) == {"search_lessons", "get_code_example", "get_mock_progress"}


def test_search_lessons_returns_results_and_records_sources(ingested_lessons):
    ctx = FakeCtx()
    results = search_lessons(ctx, "promise states pending fulfilled rejected then catch")
    assert len(results) == 3
    assert results[0].source_filename == "09-javascript-promises.md"
    data = json.loads(json.dumps([r.model_dump() for r in results]))  # JSON-serializable
    assert set(data[0]) == {"document_id", "title", "content", "similarity", "source_filename"}
    assert ctx.deps.retrieved_sources[0]["title"] == "JavaScript Promises"


def test_search_lessons_handles_backend_errors(monkeypatch):
    import app.tools.search

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(app.tools.search, "search_chunks", boom)
    assert search_lessons(FakeCtx(), "closures") == []


def test_all_required_code_examples_exist():
    topics = set(load_examples())
    assert {"closures", "promises", "array methods", "recursion", "async/await", "objects"} <= topics


@pytest.mark.parametrize("topic", ["closures", "Closure", "async await", "async/await", "array-methods", "Objects"])
def test_get_code_example_matches_topic_variants(topic):
    result = get_code_example(topic)
    assert result.found
    assert result.example.code and result.example.explanation


def test_get_code_example_unknown_topic():
    result = get_code_example("quantum computing")
    assert not result.found
    assert "closures" in result.available_topics


def test_get_mock_progress(seeded_students):
    result = get_mock_progress("student-002")
    assert result.found
    assert result.current_topic == "promises"
    assert "callbacks" in result.completed_topics


def test_get_mock_progress_unknown_student(seeded_students):
    result = get_mock_progress("student-999")
    assert not result.found and result.message


@pytest.mark.anyio
async def test_agent_can_call_all_three_tools(ingested_lessons, seeded_students):
    # TestModel calls every registered tool with generated arguments.
    deps = TutorDeps(route="concept")
    with tutor_agent.override(model=TestModel()):
        result = await tutor_agent.run("Explain closures", deps=deps)
    called = {
        part.tool_name
        for message in result.all_messages()
        for part in getattr(message, "parts", [])
        if part.part_kind == "tool-call"
    }
    assert called == {"search_lessons", "get_code_example", "get_mock_progress"}
