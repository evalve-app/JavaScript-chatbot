"""Kitaru evaluator: is StudyBot's final answer under a character limit?

Deterministic: it only measures the length of the recorded answer, so the same
session always gets the same verdict.

Register and run:
    kitaru evaluator register concise_response \
        --script evaluators/concise_response.py --entrypoint evaluate
    kitaru session evaluate --all --evaluator concise_response@1 \
        --evaluator-params 'concise_response@1={"max_chars": 850}'
"""

from typing import Any

from kitaru.json_pointer import resolve_json_pointer
from kitaru.task.evaluator import EvaluationResult, SessionView

NAME = "concise_response"
DEFAULT_MAX_CHARS = 850
ROOT_ID = "turn"  # app.recording.recorder.ROOT_ID; the root node holds the final answer


def final_answer(session: SessionView) -> str | None:
    """The answer recorded on the turn's root node, or None if there isn't one."""
    root = next((n for n in session.nodes if n.external_id == ROOT_ID and n.parent_external_id is None), None)
    if root is None or not isinstance(root.outputs, dict):
        return None
    found, answer = resolve_json_pointer(root.outputs, root.output_text_selector or "/answer")
    return answer if found and isinstance(answer, str) else None


def evaluate(session: SessionView, max_chars: int = DEFAULT_MAX_CHARS, **_: Any) -> EvaluationResult:
    """Pass when the final answer is at most `max_chars` characters (whitespace trimmed)."""
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError(f"max_chars must be a positive integer, got {max_chars!r}")

    answer = final_answer(session)
    if answer is None:
        # No verdict rather than a fail: a failed or partial turn has nothing to measure.
        return EvaluationResult(
            name=NAME, value="no_answer", passed=None, explanation="No final answer recorded on the turn."
        )

    length = len(answer.strip())
    passed = length <= max_chars
    return EvaluationResult(
        name=NAME,
        passed=passed,
        score=float(length),
        min_score=0.0,
        target_score=float(max_chars),
        explanation=f"Answer is {length} characters; limit is {max_chars} ({'within' if passed else 'over'} limit).",
    )
