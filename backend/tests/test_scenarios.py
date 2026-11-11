"""Validates the predefined scenario file (it is data for later prompt/model testing)."""

import json
from collections import Counter
from pathlib import Path

from app.tools.examples import load_examples

SCENARIOS_FILE = Path(__file__).resolve().parents[1] / "data" / "test_scenarios.json"
TOOLS = {"search_lessons", "get_code_example", "get_mock_progress"}
# The expected labels describe each scenario; there is no classifier, so they are checked as plain values.
SCOPES = {"in_scope", "out_of_scope"}
INTENTS = {"concept", "debugging", "code_generation", "quiz"}
LANGUAGES = {"javascript", "other", "unknown"}
LESSONS = {p.name for p in (SCENARIOS_FILE.parent / "lessons").glob("*.md")}


def load():
    return json.loads(SCENARIOS_FILE.read_text())["scenarios"]


def test_at_least_twenty_unique_scenarios():
    scenarios = load()
    assert len(scenarios) >= 20
    assert len({s["id"] for s in scenarios}) == len(scenarios)


def test_scenarios_are_well_formed():
    for s in load():
        expected = s["expected"]
        assert expected["scope"] in SCOPES and expected["intent"] in INTENTS, s["id"]
        assert expected["language"] in LANGUAGES, s["id"]
        assert set(s["expected_tools"]) <= TOOLS, s["id"]
        assert set(s.get("expected_sources", [])) <= LESSONS, s["id"]
        assert s["checks"], s["id"]
        if expected["scope"] == "out_of_scope":
            assert s["expected_tools"] == [], s["id"]


def test_required_categories_are_covered():
    counts = Counter(s["category"] for s in load())
    for category in ["classification", "concept", "code_generation", "debugging", "quiz", "tool_usage"]:
        assert counts[category] >= 1, category
    assert any("history" in s for s in load()), "needs follow-up scenarios"
    assert any(len(s["expected_tools"]) > 1 for s in load()), "needs a multi-tool scenario"


def test_examples_file_matches_tool():
    assert len(load_examples()) >= 6
