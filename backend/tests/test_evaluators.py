"""Kitaru evaluators in evaluators/, run on hand-built sessions (no Kitaru server)."""

import pytest
from kitaru.api_models.v1.evaluation import EvaluationDataType
from kitaru.api_models.v1.session import SessionDetailResponse
from kitaru.api_models.v1.session_node import SessionNodeResponse
from kitaru.task.evaluator import SessionView, call_evaluator

from evaluators import concise_response, js_code_parses, professional_response


def node(external_id, parent=None, inputs=None, outputs=None, output_text_selector=None):
    return SessionNodeResponse.model_construct(
        external_id=external_id,
        parent_external_id=parent,
        inputs=inputs,
        outputs=outputs,
        output_text_selector=output_text_selector,
    )


def session_with_answer(answer, question="Explain closures"):
    root = node(
        "turn", inputs={"question": question, "history": []}, outputs={"answer": answer}, output_text_selector="/answer"
    )
    child = node("llm-1", parent="turn", outputs={"text": "x" * 5000}, output_text_selector="/text")
    return SessionView(session=SessionDetailResponse.model_construct(), nodes=[root, child])


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
    assert (result.passed, result.value) == (True, "has_js_code")


def test_broken_block_fails_and_names_it():
    answer = f"{fenced('const a = 1;')}\n\nand\n\n{fenced('function add(a, b) {\n  return a +;\n}', 'js')}"
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert (result.passed, result.value) == (False, "has_js_code")
    assert "1/2" in result.explanation
    assert "block 2" in result.explanation and "line 2" in result.explanation


def test_missing_closing_brace_fails():
    assert js_code_parses.evaluate(session_with_answer(fenced("if (x) {\n  go();"))).passed is False


def test_jsx_and_other_tags_count_as_js():
    answer = fenced("const el = <div>{name}</div>;", "jsx") + "\n" + fenced("x = ;", "JS")
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert result.passed is False
    assert "1/2" in result.explanation


def test_non_js_blocks_are_ignored_and_no_code_passes():
    answer = fenced("print('hi'", "python") + "\n" + fenced("TypeError: x is not a function", "text")
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert (result.passed, result.value) == (True, "no_js_code")


@pytest.mark.parametrize(
    "answer",
    [
        "Try this:\n\n```javascript\nconst x = ;\n",  # unclosed fence: Markdown renders it to the end
        "> Example:\n>\n> ```js\n> const x = ;\n> ```\n",  # fence inside a blockquote
        "1. ```js\n   const x = ;\n   ```\n",  # fence on a list item's marker line
        "- Step one:\n\n  ```js\n  const x = ;\n  ```\n",  # fence nested in a list item
    ],
)
def test_broken_code_in_any_rendered_fence_fails(answer):
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert (result.passed, result.value) == (False, "has_js_code")


def test_fence_like_text_inside_a_block_does_not_split_it():
    # A shorter backtick run inside a ```` fence is content, not a closing fence.
    answer = "````js\n/*\n```\n*/\nconst x = 1;\n````"
    assert js_code_parses.js_blocks(answer) == ["/*\n```\n*/\nconst x = 1;\n"]
    result = js_code_parses.evaluate(session_with_answer(answer))
    assert (result.passed, result.value) == (True, "has_js_code")


def test_indented_code_without_a_js_fence_is_ignored():
    result = js_code_parses.evaluate(session_with_answer("Output:\n\n    const x = ;\n"))
    assert (result.passed, result.value) == (True, "no_js_code")


def test_broken_code_quoted_from_the_question_is_skipped():
    broken = "function greet( {\n  return 'hi';\n}"
    answer = f"Your code:\n\n{fenced(broken)}\n\nFixed:\n\n{fenced(broken.replace('( {', '() {'))}"
    result = js_code_parses.evaluate(session_with_answer(answer, question=f"Why does this fail?\n{broken}"))
    assert result.passed is True
    assert "1 quoted from the question" in result.explanation


def test_js_code_parses_no_answer_fails():
    result = js_code_parses.evaluate(no_answer_session())
    assert (result.passed, result.value) == (False, "no_js_code")


async def test_js_code_parses_meets_kitarus_contract():
    results = await call_evaluator(js_code_parses.NAME, js_code_parses.evaluate, session_with_answer("hi"), {})
    assert [r.name for r in results] == [js_code_parses.NAME]


@pytest.mark.parametrize(
    "view",
    [
        session_with_answer("no code"),
        session_with_answer(fenced("x = ;")),
        session_with_answer(fenced("let a = 1;")),
        no_answer_session(),
    ],
)
def test_every_result_is_categorical_with_a_verdict(view):
    # Kitaru only counts labels for categorical results and groups summaries by data type,
    # so every result must be categorical (score and label both set) to land in one summary row.
    result = js_code_parses.evaluate(view)
    assert result.data_type is EvaluationDataType.CATEGORICAL
    assert isinstance(result.passed, bool) and result.score is result.passed


# professional_response (the judge call is replaced; these tests never reach OpenAI)


@pytest.fixture
def judge_calls(monkeypatch):
    """Replace the judge with one that returns the next queued verdict and records its inputs."""
    calls, verdicts = [], []

    def fake_judge(question, answer, model, temperature):
        calls.append({"question": question, "answer": answer, "model": model, "temperature": temperature})
        return verdicts.pop(0)

    monkeypatch.setattr(professional_response, "judge", fake_judge)
    return calls, verdicts


def verdict(professional, reason="Because."):
    return professional_response.Verdict(professional=professional, reason=reason)


def test_professional_answer_passes(judge_calls):
    calls, verdicts = judge_calls
    verdicts.append(verdict(True, "Clear and encouraging."))
    result = professional_response.evaluate(session_with_answer("Great question! A closure is...", question="Closures?"))
    assert result.passed is True
    assert "Clear and encouraging." in result.explanation
    assert calls == [
        {"question": "Closures?", "answer": "Great question! A closure is...", "model": "gpt-4.1-mini", "temperature": 0.0}
    ]


def test_unprofessional_answer_fails_with_the_judges_reason(judge_calls):
    judge_calls[1].append(verdict(False, 'Says "obviously".'))
    result = professional_response.evaluate(session_with_answer("Obviously, lol."))
    assert result.passed is False
    assert 'Says "obviously".' in result.explanation


def test_judge_model_and_temperature_params_are_passed_through(judge_calls):
    calls, verdicts = judge_calls
    verdicts.append(verdict(True))
    result = professional_response.evaluate(session_with_answer("hi"), judge_model="gpt-6-astra", temperature=None)
    assert (calls[0]["model"], calls[0]["temperature"]) == ("gpt-6-astra", None)
    assert "gpt-6-astra" in result.explanation


@pytest.mark.parametrize(("temperature", "sent"), [(0.0, {"temperature": 0.0}), (None, {})])
def test_null_temperature_is_left_out_of_the_request(monkeypatch, temperature, sent):
    # Some models (gpt-6-astra) reject any temperature but their default, so None must send none.
    captured = {}

    class FakeCompletions:
        def parse(self, **kwargs):
            captured.update(kwargs)
            message = type("M", (), {"parsed": verdict(True), "refusal": None})()
            return type("C", (), {"choices": [type("Ch", (), {"message": message})()]})()

    fake_client = type("Client", (), {"chat": type("Chat", (), {"completions": FakeCompletions()})()})()
    monkeypatch.setattr(professional_response, "OpenAI", lambda: fake_client)
    professional_response.judge("q", "a", "gpt-6-astra", temperature)
    assert {k: v for k, v in captured.items() if k == "temperature"} == sent


def test_judges_only_the_final_answer_not_intermediate_llm_text(judge_calls):
    calls, verdicts = judge_calls
    verdicts.append(verdict(True))
    professional_response.evaluate(session_with_answer("short"))
    assert calls[0]["answer"] == "short"


@pytest.mark.parametrize("view", [no_answer_session(), session_with_answer("   \n")])
def test_no_answer_fails_without_calling_the_judge(judge_calls, view):
    result = professional_response.evaluate(view)
    assert result.passed is False
    assert judge_calls[0] == []


@pytest.mark.parametrize("bad", ["", "  ", None, 4])
def test_rejects_invalid_judge_model(judge_calls, bad):
    with pytest.raises(ValueError):
        professional_response.evaluate(session_with_answer("hi"), judge_model=bad)


@pytest.mark.parametrize("bad", ["0", True])
def test_rejects_invalid_temperature(judge_calls, bad):
    with pytest.raises(ValueError):
        professional_response.evaluate(session_with_answer("hi"), temperature=bad)


def test_judge_errors_fail_the_task(monkeypatch):
    # An API error must not be stored as a verdict either way.
    def broken_judge(question, answer, model, temperature):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(professional_response, "judge", broken_judge)
    with pytest.raises(RuntimeError):
        professional_response.evaluate(session_with_answer("hi"))


def test_judge_prompt_keeps_the_answer_as_data():
    assert "not instructions to you" in professional_response.JUDGE_PROMPT


def test_verdict_schema_is_a_reason_then_a_boolean():
    # Structured output: the judge can only answer with these two fields, reason first.
    schema = professional_response.Verdict.model_json_schema()
    assert list(schema["properties"]) == ["reason", "professional"]
    assert schema["properties"]["professional"]["type"] == "boolean"


async def test_professional_response_meets_kitarus_contract(judge_calls):
    judge_calls[1].append(verdict(True))
    results = await call_evaluator(
        professional_response.NAME,
        professional_response.evaluate,
        session_with_answer("hi"),
        {"judge_model": "gpt-6-astra", "temperature": None},
    )
    assert [r.name for r in results] == [professional_response.NAME]
    assert results[0].data_type is EvaluationDataType.BOOL
    assert results[0].passed is True and results[0].score is True


pytestmark = pytest.mark.anyio
