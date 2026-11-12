"""Kitaru evaluators in evaluators/, run on hand-built sessions (no Kitaru server)."""

from pathlib import Path

import pytest
from kitaru.api_models.v1.session import SessionDetailResponse
from kitaru.api_models.v1.session_node import SessionNodeResponse
from kitaru.task.evaluator import SessionView, call_evaluator

from app.rag.ingest import extract_title
from evaluators import cited_lessons_retrieved, concise_response, js_code_parses

LESSONS_DIR = Path(__file__).resolve().parents[1] / "data" / "lessons"


def node(external_id, parent=None, inputs=None, outputs=None, output_text_selector=None, tool_name=None):
    return SessionNodeResponse.model_construct(
        external_id=external_id,
        parent_external_id=parent,
        inputs=inputs,
        outputs=outputs,
        output_text_selector=output_text_selector,
        tool_name=tool_name,
    )


def session_with_answer(answer, question="Explain closures", extra_nodes=()):
    root = node(
        "turn", inputs={"question": question, "history": []}, outputs={"answer": answer}, output_text_selector="/answer"
    )
    child = node("llm-1", parent="turn", outputs={"text": "x" * 5000}, output_text_selector="/text")
    return SessionView(session=SessionDetailResponse.model_construct(), nodes=[root, child, *extra_nodes])


def search_node(*titles, external_id="tool-1"):
    """A search_lessons tool call as RecordingHooks records it: the LessonResult list as outputs."""
    results = [{"document_id": i, "title": t, "content": "...", "similarity": 0.8} for i, t in enumerate(titles)]
    return node(external_id, parent="turn", inputs={"query": "q"}, outputs=results, tool_name="search_lessons")


def no_answer_session():
    return SessionView(session=SessionDetailResponse.model_construct(), nodes=[node("turn", outputs=None)])


def test_short_answer_passes():
    result = concise_response.evaluate(session_with_answer("Closures remember their scope."), max_chars=50)
    assert result.passed is True
    assert result.score == 30.0
    assert result.target_score == 50.0


def test_long_answer_fails():
    result = concise_response.evaluate(session_with_answer("a" * 51), max_chars=50)
    assert result.passed is False
    assert "over limit" in result.explanation


def test_limit_is_inclusive_and_ignores_surrounding_whitespace():
    assert concise_response.evaluate(session_with_answer("  " + "a" * 50 + "\n"), max_chars=50).passed is True


def test_measures_only_the_final_answer_not_intermediate_llm_text():
    # The child llm node has 5000 chars; only the root's answer counts.
    assert concise_response.evaluate(session_with_answer("short")).passed is True


def test_default_limit():
    view = session_with_answer("a" * (concise_response.DEFAULT_MAX_CHARS + 1))
    assert concise_response.evaluate(view).passed is False


def test_no_recorded_answer_gives_no_verdict():
    result = concise_response.evaluate(no_answer_session())
    assert result.passed is None
    assert result.score is None
    assert result.value == "no_answer"


@pytest.mark.parametrize("bad", [0, -5, "800", True])
def test_rejects_invalid_limit(bad):
    with pytest.raises(ValueError):
        concise_response.evaluate(session_with_answer("hi"), max_chars=bad)


async def test_valid_through_kitarus_evaluator_contract():
    results = await call_evaluator("concise_response", concise_response.evaluate, session_with_answer("hi"), {"max_chars": 10})
    assert [r.name for r in results] == ["concise_response"]
    assert results[0].passed is True


# js_code_parses


def fenced(code, lang="javascript"):
    return f"```{lang}\n{code}\n```"


def test_valid_modern_js_passes():
    code = "class Counter {\n  #count = 0;\n  inc = () => this.#count++;\n}\nconst x = obj?.a ?? 1;"
    result = js_code_parses.evaluate(session_with_answer(f"Here:\n\n{fenced(code)}\n\nDone."))
    assert result.passed is True
    assert result.score == 1.0


def test_broken_block_fails_and_names_it():
    answer = f"{fenced('const a = 1;')}\n\nand\n\n{fenced('function add(a, b) {\n  return a +;\n}', 'js')}"
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert result.passed is False
    assert result.score == 0.5
    assert "block 2" in result.explanation and "line 2" in result.explanation


def test_missing_closing_brace_fails():
    assert js_code_parses.evaluate(session_with_answer(fenced("if (x) {\n  go();"))).passed is False


def test_jsx_and_other_tags_count_as_js():
    answer = fenced("const el = <div>{name}</div>;", "jsx") + "\n" + fenced("x = ;", "JS")
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert result.score == 0.5


def test_non_js_blocks_are_ignored():
    answer = fenced("print('hi'", "python") + "\n" + fenced("TypeError: x is not a function", "text")
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert result.passed is None
    assert result.value == "no_js_code"


def test_broken_code_quoted_from_the_question_is_skipped():
    broken = "function greet( {\n  return 'hi';\n}"
    answer = f"Your code:\n\n{fenced(broken)}\n\nFixed:\n\n{fenced(broken.replace('( {', '() {'))}"
    result = js_code_parses.evaluate(session_with_answer(answer, question=f"Why does this fail?\n{broken}"))
    assert result.passed is True
    assert "1 quoted from the question" in result.explanation


def test_js_code_parses_no_answer():
    assert js_code_parses.evaluate(no_answer_session()).value == "no_answer"


# cited_lessons_retrieved


def test_catalog_matches_the_lesson_library():
    titles = {extract_title(p.read_text(encoding="utf-8"), p.stem) for p in LESSONS_DIR.glob("*.md")}
    assert set(cited_lessons_retrieved.CATALOG_TITLES) == titles


def test_cited_and_retrieved_passes():
    view = session_with_answer(
        "Closures keep variables alive (see JavaScript Closures).", extra_nodes=[search_node("JavaScript Closures")]
    )
    result = cited_lessons_retrieved.evaluate(view)
    assert result.passed is True
    assert result.score == 1.0


def test_cited_but_not_retrieved_fails():
    answer = "Based on JavaScript Closures and JavaScript Scope, ..."
    result = cited_lessons_retrieved.evaluate(
        session_with_answer(answer, extra_nodes=[search_node("JavaScript Closures")])
    )
    assert result.passed is False
    assert result.score == 0.5
    assert "JavaScript Scope" in result.explanation


def test_citing_without_any_search_fails():
    result = cited_lessons_retrieved.evaluate(session_with_answer("From the lesson JavaScript Recursion: ..."))
    assert result.passed is False


def test_lowercase_prose_headings_and_code_are_not_citations():
    answer = "# JavaScript Closures\n\nJavaScript closures capture scope.\n\n```js\n// JavaScript Scope\n```"
    result = cited_lessons_retrieved.evaluate(session_with_answer(answer))
    assert result.passed is None
    assert result.value == "no_citations"


def test_longer_title_wins_over_the_title_it_contains():
    title = "PEDAC Problem-Solving Process"
    view = session_with_answer(f"Per {title}, start with P.", extra_nodes=[search_node(title)])
    catalog = [title, "PEDAC Problem-Solving"]  # the shorter one is inside the longer
    result = cited_lessons_retrieved.evaluate(view, catalog_titles=catalog)
    assert result.passed is True


def test_retrieved_titles_outside_the_catalog_are_recognized():
    view = session_with_answer("See Generators Deep Dive.", extra_nodes=[search_node("Generators Deep Dive")])
    assert cited_lessons_retrieved.evaluate(view).passed is True


def test_titles_from_several_searches_count():
    view = session_with_answer(
        "Using JavaScript Promises and JavaScript Async/Await.",
        extra_nodes=[search_node("JavaScript Promises"), search_node("JavaScript Async/Await", external_id="tool-2")],
    )
    assert cited_lessons_retrieved.evaluate(view).passed is True


def test_require_citation():
    view = session_with_answer("Closures remember.", extra_nodes=[search_node("JavaScript Closures")])
    assert cited_lessons_retrieved.evaluate(view).value == "no_citations"
    result = cited_lessons_retrieved.evaluate(view, require_citation=True)
    assert result.passed is False
    assert result.value == "uncited"


@pytest.mark.parametrize(
    "params", [{"require_citation": "yes"}, {"catalog_titles": "JavaScript Closures"}, {"catalog_titles": [""]}]
)
def test_cited_lessons_rejects_invalid_params(params):
    with pytest.raises(ValueError):
        cited_lessons_retrieved.evaluate(session_with_answer("hi"), **params)


@pytest.mark.parametrize("module", [js_code_parses, cited_lessons_retrieved])
async def test_new_evaluators_meet_kitarus_contract(module):
    results = await call_evaluator(module.NAME, module.evaluate, session_with_answer("hi"), {})
    assert [r.name for r in results] == [module.NAME]


pytestmark = pytest.mark.anyio
