"""Kitaru evaluators in evaluators/, run on hand-built sessions (no Kitaru server)."""

import pytest
from kitaru.api_models.v1.session import SessionDetailResponse
from kitaru.api_models.v1.session_node import SessionNodeResponse
from kitaru.task.evaluator import SessionView, call_evaluator

from evaluators import concise_response


def node(external_id, parent=None, outputs=None, output_text_selector=None):
    return SessionNodeResponse.model_construct(
        external_id=external_id,
        parent_external_id=parent,
        outputs=outputs,
        output_text_selector=output_text_selector,
    )


def session_with_answer(answer):
    root = node("turn", outputs={"answer": answer}, output_text_selector="/answer")
    child = node("llm-1", parent="turn", outputs={"text": "x" * 5000}, output_text_selector="/text")
    return SessionView(session=SessionDetailResponse.model_construct(), nodes=[root, child])


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
    failed_turn = SessionView(session=SessionDetailResponse.model_construct(), nodes=[node("turn", outputs=None)])
    result = concise_response.evaluate(failed_turn)
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


pytestmark = pytest.mark.anyio
