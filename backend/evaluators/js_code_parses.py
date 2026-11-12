# /// script
# dependencies = ["tree-sitter==0.26.1", "tree-sitter-javascript==0.25.0"]
# ///
"""Kitaru evaluator: does every JavaScript code block in StudyBot's answer parse?

Deterministic: each ```js / ```javascript (also jsx, mjs, cjs) block is parsed with
tree-sitter's JavaScript grammar, which handles modern syntax (?., ??, class fields, JSX).
A block counts as broken if the parse has any ERROR or MISSING node. This checks syntax
only: code that parses can still be wrong.

Blocks that appear verbatim in the student's question are skipped, so quoting the
student's own broken code back to them in a debugging answer is not a failure.

Every result has a pass/fail and a label: has_js_code or no_js_code.

The worker installs the dependencies above from the inline script block.

Register and run:
    kitaru evaluator register studybot-js-code-parses \
        --script evaluators/js_code_parses.py --entrypoint evaluate
    kitaru session evaluate --all --evaluator studybot-js-code-parses@1
"""

import re
from typing import Any

import tree_sitter
import tree_sitter_javascript
from kitaru.json_pointer import resolve_json_pointer
from kitaru.task.evaluator import EvaluationResult, SessionView

NAME = "js_code_parses"
ROOT_ID = "turn"  # app.recording.recorder.ROOT_ID; the root node holds the question and final answer
JS_LANGUAGES = {"js", "javascript", "jsx", "mjs", "cjs"}

# An opening fence (``` or ~~~, optional language tag), its body, and the matching closing fence.
FENCE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})[ \t]*(?P<lang>[\w+-]*)[^\n]*\n(?P<code>.*?)^[ \t]*(?P=fence)[ \t]*$", re.MULTILINE | re.DOTALL)

PARSER = tree_sitter.Parser(tree_sitter.Language(tree_sitter_javascript.language()))


def root_node(session: SessionView):
    return next((n for n in session.nodes if n.external_id == ROOT_ID and n.parent_external_id is None), None)


def final_answer(session: SessionView) -> str | None:
    """The answer recorded on the turn's root node, or None if there isn't one."""
    root = root_node(session)
    if root is None or not isinstance(root.outputs, dict):
        return None
    found, answer = resolve_json_pointer(root.outputs, root.output_text_selector or "/answer")
    return answer if found and isinstance(answer, str) else None


def question(session: SessionView) -> str:
    root = root_node(session)
    value = root.inputs.get("question") if root is not None and isinstance(root.inputs, dict) else None
    return value if isinstance(value, str) else ""


def js_blocks(markdown: str) -> list[str]:
    return [m["code"] for m in FENCE.finditer(markdown) if m["lang"].lower() in JS_LANGUAGES]


def first_error(code: str) -> str | None:
    """None if the code parses, else where the first syntax error is (1-based line)."""
    tree = PARSER.parse(code.encode("utf-8"))
    if not tree.root_node.has_error:
        return None
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.is_error or node.is_missing:
            kind = f"missing {node.type!r}" if node.is_missing else "unexpected syntax"
            return f"{kind} at line {node.start_point.row + 1}"
        stack.extend(reversed([c for c in node.children if c.has_error or c.is_missing]))
    return "syntax error"


def _normalize(code: str) -> str:
    return " ".join(code.split())


def result(passed: bool, label: str, explanation: str) -> EvaluationResult:
    # score mirrors passed: a score plus a label makes Kitaru store the result as categorical,
    # so experiment summaries count the labels and report one pass rate for every session.
    return EvaluationResult(name=NAME, passed=passed, score=passed, value=label, explanation=explanation)


def evaluate(session: SessionView, **_: Any) -> EvaluationResult:
    """Pass when every JavaScript block the answer wrote (not quoted from the question) parses.

    Label has_js_code or no_js_code. An answer with no code of its own passes; a turn with
    no recorded answer fails.
    """
    answer = final_answer(session)
    if answer is None:
        return result(False, "no_js_code", "No final answer recorded on the turn.")

    asked = _normalize(question(session))
    blocks = [b for b in js_blocks(answer) if b.strip()]
    checked = [b for b in blocks if _normalize(b) not in asked]
    skipped = len(blocks) - len(checked)
    if not checked:
        note = f" ({skipped} quoted from the question, skipped)" if skipped else ""
        return result(True, "no_js_code", f"No JavaScript code blocks to check{note}.")

    errors = [(i, err) for i, block in enumerate(checked, 1) if (err := first_error(block)) is not None]
    valid = len(checked) - len(errors)
    details = "; ".join(f"block {i}: {err}" for i, err in errors)
    explanation = f"{valid}/{len(checked)} JavaScript blocks parse" + (f" ({details})" if details else "")
    if skipped:
        explanation += f"; {skipped} quoted from the question, skipped"
    return result(not errors, "has_js_code", explanation + ".")
