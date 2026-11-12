"""Kitaru evaluator: were the lessons StudyBot's answer cites actually retrieved?

The tutor prompt says "Mention lesson titles you relied on." This checks that every
lesson title named in the final answer came back from a `search_lessons` call in the
same session, so the answer doesn't claim a source it never saw.

Deterministic. How it decides:
- Retrieved: the `title` of every result in the session's search_lessons tool outputs
  (what the model saw, including results a replay mocked).
- Cited: a known lesson title appearing exactly (case-sensitive) in the answer, outside
  code blocks and Markdown headings. Case-sensitive so prose like "JavaScript closures
  capture..." doesn't count as citing "JavaScript Closures". Known titles are
  CATALOG_TITLES (data/lessons) plus anything retrieved.

Limits: a made-up title that isn't in the catalog can't be recognized, and a lesson
retrieved in an earlier turn (a different session) counts as not retrieved.

Every result has a pass/fail and a label: has_citation or no_citation.

Params:
    require_citation  also fail when lessons were retrieved but none is cited (default false)
    catalog_titles    replace CATALOG_TITLES when the lesson library changes

Register and run:
    kitaru evaluator register studybot-cited-lessons-retrieved \
        --script evaluators/cited_lessons_retrieved.py --entrypoint evaluate
    kitaru session evaluate --all --evaluator studybot-cited-lessons-retrieved@1
"""

import re
from typing import Any

from kitaru.json_pointer import resolve_json_pointer
from kitaru.task.evaluator import EvaluationResult, SessionView

NAME = "cited_lessons_retrieved"
ROOT_ID = "turn"  # app.recording.recorder.ROOT_ID; the root node holds the final answer
SEARCH_TOOL = "search_lessons"

# The "# " title of each file in backend/data/lessons, as app.rag.ingest.extract_title reads it.
CATALOG_TITLES = (
    "JavaScript Variables and Data Types",
    "JavaScript Functions and Parameters",
    "JavaScript Scope",
    "JavaScript Closures",
    "JavaScript Hoisting",
    "JavaScript Arrays and Array Methods",
    "JavaScript Objects",
    "JavaScript Callbacks",
    "JavaScript Promises",
    "JavaScript Async/Await",
    "JavaScript Event Loop",
    "JavaScript Prototypes and Classes",
    "JavaScript Error Handling",
    "JavaScript DOM Manipulation",
    "JavaScript Recursion",
    "PEDAC Problem-Solving Process",
    "PEDAC Walkthrough: Comparing Version Numbers",
    "PEDAC: Understanding Problems and Writing Test Cases",
    "PEDAC: Asking Clarifying Questions",
    "Introduction to the PEDAC Process: Palindrome Substrings",
    "PEDAC Guided Practice: Leftover Blocks",
    "PEDAC Guided Practice: Sort by Most Adjacent Consonants",
)

FENCED_CODE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[ \t]*$", re.MULTILINE | re.DOTALL)
HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t].*$", re.MULTILINE)


def final_answer(session: SessionView) -> str | None:
    """The answer recorded on the turn's root node, or None if there isn't one."""
    root = next((n for n in session.nodes if n.external_id == ROOT_ID and n.parent_external_id is None), None)
    if root is None or not isinstance(root.outputs, dict):
        return None
    found, answer = resolve_json_pointer(root.outputs, root.output_text_selector or "/answer")
    return answer if found and isinstance(answer, str) else None


def retrieved_titles(session: SessionView) -> set[str]:
    titles = set()
    for node in session.nodes:
        if node.tool_name != SEARCH_TOOL or not isinstance(node.outputs, list):
            continue
        titles.update(r["title"] for r in node.outputs if isinstance(r, dict) and isinstance(r.get("title"), str))
    return titles


def cited_titles(answer: str, known: set[str]) -> set[str]:
    """Known titles named in the answer's prose; a longer title wins over one it contains."""
    text = HEADING.sub("", FENCED_CODE.sub("", answer))
    cited = set()
    for title in sorted(known, key=len, reverse=True):
        if title in text:
            cited.add(title)
            text = text.replace(title, "\0")
    return cited


def result(passed: bool, label: str, explanation: str) -> EvaluationResult:
    # score mirrors passed: a score plus a label makes Kitaru store the result as categorical,
    # so experiment summaries count the labels and report one pass rate for every session.
    return EvaluationResult(name=NAME, passed=passed, score=passed, value=label, explanation=explanation)


def evaluate(
    session: SessionView, require_citation: bool = False, catalog_titles: list[str] | None = None, **_: Any
) -> EvaluationResult:
    """Pass when every cited lesson title was retrieved in this session.

    Label has_citation or no_citation. An answer citing nothing passes, unless
    require_citation is set and it retrieved lessons; a turn with no recorded answer fails.
    """
    if catalog_titles is not None and not (
        isinstance(catalog_titles, list) and all(isinstance(t, str) and t.strip() for t in catalog_titles)
    ):
        raise ValueError("catalog_titles must be a list of non-empty strings")
    if not isinstance(require_citation, bool):
        raise ValueError(f"require_citation must be true or false, got {require_citation!r}")

    answer = final_answer(session)
    if answer is None:
        return result(False, "no_citation", "No final answer recorded on the turn.")

    retrieved = retrieved_titles(session)
    cited = cited_titles(answer, set(CATALOG_TITLES if catalog_titles is None else catalog_titles) | retrieved)
    not_retrieved = sorted(cited - retrieved)

    if not cited:
        if require_citation and retrieved:
            listed = ", ".join(sorted(retrieved))
            return result(False, "no_citation", f"Retrieved {len(retrieved)} lesson(s) but cited none: {listed}.")
        return result(True, "no_citation", "The answer names no lesson titles.")

    if not_retrieved:
        return result(False, "has_citation", f"Cited but not retrieved: {', '.join(not_retrieved)}.")
    return result(True, "has_citation", f"All {len(cited)} cited lesson(s) were retrieved: {', '.join(sorted(cited))}.")
