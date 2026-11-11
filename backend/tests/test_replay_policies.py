"""Replay overrides and tool policies on the real tutor agent (fake models, fake Kitaru)."""

import pytest
from kitaru.api_models.v1.replay import ToolLookupMatch, ToolLookupResponse
from kitaru.api_models.v1.replay_config import (
    HistoryConfig,
    LLMConfig,
    PassthroughConfig,
    ReplayOverride,
    StaticCase,
    StaticConfig,
    ToolPolicy,
)
from kitaru.api_models.v1.session_node import NodeStatus
from kitaru.cache_keys import compute_tool_cache_key
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import app.recording.recorder as rec
from app.agents.deps import TutorDeps
from app.agents.tutor import tutor_agent
from app.recording.hooks import RecordingHooks
from app.recording.replay import (
    RecordedToolFailure,
    ReplayConfigError,
    ReplayPlan,
    ToolPolicyMissError,
)
from tests.test_recording import FakeKitaru, only_session, recorder_for

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def no_backoff():
    rec.reset_backoff()
    yield
    rec.reset_backoff()


class FakeLookup:
    """Recorded tool results keyed by (cache_key, occurrence)."""

    def __init__(self, recorded=None):
        self.recorded = recorded or {}
        self.calls = []

    async def __call__(self, tool_name, cache_key, occurrence):
        self.calls.append((tool_name, cache_key, occurrence))
        match = self.recorded.get((cache_key, occurrence))
        return ToolLookupResponse(match=match)


def plan(override=None, default=None, tools=None, lookup=None):
    p = ReplayPlan(
        override=override,
        tool_policy=ToolPolicy(default=default or PassthroughConfig(), tools=tools or {}),
        lookup=lookup or FakeLookup(),
    )
    p.check()
    return p


def calls_tool_then_answers(tool_name, args, times=1):
    """Fake model: asks for the tool `times` times (one per step), then answers with what it saw."""

    def respond(messages, info: AgentInfo):
        returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
        if len(returns) < times:
            return ModelResponse(parts=[ToolCallPart(tool_name, args)])
        return ModelResponse(parts=[TextPart(f"saw: {[r.content for r in returns]}")])

    return FunctionModel(respond)


async def run_tutor(recorder, replay_plan, model, model_factory=None):
    span = recorder.begin_span("tutor")
    hooks = RecordingHooks(recorder, span, "tutor", replay=replay_plan, model_factory=model_factory)
    try:
        with tutor_agent.override(model=model):
            return await tutor_agent.run("q", deps=TutorDeps(), capabilities=[hooks])
    finally:
        recorder.end_span(span)


@pytest.fixture
def live_tool_must_not_run(monkeypatch):
    import app.tools.examples as examples

    def boom(*a, **k):
        raise AssertionError("live tool ran but the policy should have answered")

    monkeypatch.setattr(examples, "load_examples", boom)


# ---------- up-front checks ----------


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (dict(default=LLMConfig(model="gpt-4o-mini")), "'llm' tool policy"),
        (dict(tools={"get_code_example": LLMConfig(model="x")}), "'llm' tool policy"),
        (dict(tools={"delete_database": PassthroughConfig()}), "unknown tools: delete_database"),
        (dict(override=ReplayOverride(model_params={"frequency_penalty": 1})), "Unsupported model_params"),
        (dict(override=ReplayOverride(model="anthropic:claude")), "Only OpenAI models"),
        (dict(override=ReplayOverride(model={"gpt-4o-mini": "google:gemini"})), "Only OpenAI models"),
        (dict(override=ReplayOverride(prompt="  ")), "prompt is empty"),
        (dict(override=ReplayOverride(system_prompt="")), "system_prompt is empty"),
    ],
)
def test_unsupported_replays_are_rejected_up_front(kwargs, message):
    with pytest.raises(ReplayConfigError, match=message):
        plan(**kwargs)


def test_model_for():
    assert plan(override=ReplayOverride(model="openai:gpt-4.1-mini")).model_for("gpt-4o-mini") == "gpt-4.1-mini"
    mapped = plan(override=ReplayOverride(model={"openai:gpt-4o-mini": "gpt-4.1-mini"}))
    assert mapped.model_for("gpt-4o-mini") == "gpt-4.1-mini"
    assert mapped.model_for("gpt-4o") is None
    assert plan().model_for("gpt-4o-mini") is None


# ---------- model overrides ----------


async def test_model_override_really_changes_the_model():
    original = FunctionModel(lambda m, i: ModelResponse(parts=[TextPart("from original")]), model_name="gpt-4o-mini")
    swapped = FunctionModel(lambda m, i: ModelResponse(parts=[TextPart("from override")]), model_name="gpt-4.1-mini")
    built = []

    def factory(name):
        built.append(name)
        return swapped

    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    result = await run_tutor(
        recorder, plan(override=ReplayOverride(model={"gpt-4o-mini": "gpt-4.1-mini"})), original, factory
    )
    await recorder.finish(answer=result.output)

    assert result.output == "from override" and built == ["gpt-4.1-mini"]
    call = next(n for n in only_session(fake)["nodes"].values() if n.node_type.value == "llm_call")
    assert call.requested_model == "gpt-4o-mini"
    assert call.attributes["replay.override"] == {"model": "gpt-4.1-mini"}
    assert call.name == "chat gpt-4o-mini"  # named after the requested model


async def test_model_params_override_reaches_the_model():
    seen = {}

    def respond(messages, info: AgentInfo):
        seen["settings"] = info.model_settings
        return ModelResponse(parts=[TextPart("ok")])

    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    await run_tutor(recorder, plan(override=ReplayOverride(model_params={"temperature": 0.0, "seed": 7})), FunctionModel(respond))
    await recorder.finish(answer="ok")

    assert seen["settings"]["temperature"] == 0.0 and seen["settings"]["seed"] == 7
    call = next(n for n in only_session(fake)["nodes"].values() if n.node_type.value == "llm_call")
    assert call.model_params == {"temperature": 0.0, "seed": 7}


# ---------- tool policies ----------


ARGS = {"topic": "closures"}
KEY = compute_tool_cache_key("get_code_example", ARGS)


def recorded(result, status=NodeStatus.COMPLETED, error=None):
    return ToolLookupMatch(result=result, status=status, error=error)


async def test_history_hit_returns_recorded_results_in_order(live_tool_must_not_run):
    lookup = FakeLookup({(KEY, 0): recorded("first recording"), (KEY, 1): recorded("second recording")})
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    result = await run_tutor(
        recorder,
        plan(default=HistoryConfig(scope="baseline", on_miss="fail"), lookup=lookup),
        calls_tool_then_answers("get_code_example", ARGS, times=2),
    )
    await recorder.finish(answer=result.output)

    assert result.output == "saw: ['first recording', 'second recording']"
    assert [c[2] for c in lookup.calls] == [0, 1]  # occurrence advances per identical call
    tools = [n for n in only_session(fake)["nodes"].values() if n.node_type.value == "tool_call"]
    assert all(t.attributes["replay.policy"] == "history" and t.attributes["replay.mocked"] for t in tools)
    # The key Kitaru would compute from the recorded node equals the key we looked up.
    assert compute_tool_cache_key("get_code_example", tools[0].inputs) == KEY


async def test_history_wider_scope_sends_no_occurrence(live_tool_must_not_run):
    lookup = FakeLookup({(KEY, None): recorded("agent-wide")})
    recorder = recorder_for(FakeKitaru(), secrets=[])
    await recorder.start(question="q", history=[])
    result = await run_tutor(
        recorder,
        plan(default=HistoryConfig(scope="agent", on_miss="fail"), lookup=lookup),
        calls_tool_then_answers("get_code_example", ARGS),
    )
    assert "agent-wide" in result.output and lookup.calls[0][2] is None


async def test_history_miss_fail_stops_the_turn(live_tool_must_not_run):
    recorder = recorder_for(FakeKitaru(), secrets=[])
    await recorder.start(question="q", history=[])
    with pytest.raises(ToolPolicyMissError, match="No history result for tool 'get_code_example'"):
        await run_tutor(
            recorder,
            plan(default=HistoryConfig(scope="baseline", on_miss="fail")),
            calls_tool_then_answers("get_code_example", ARGS),
        )


async def test_history_miss_error_result_is_given_to_the_agent(live_tool_must_not_run):
    recorder = recorder_for(FakeKitaru(), secrets=[])
    await recorder.start(question="q", history=[])
    result = await run_tutor(
        recorder,
        plan(default=HistoryConfig(scope="baseline", on_miss="error_result")),
        calls_tool_then_answers("get_code_example", ARGS),
    )
    assert "No history result for tool 'get_code_example'" in result.output


async def test_history_miss_passthrough_runs_the_real_tool():
    recorder = recorder_for(FakeKitaru(), secrets=[])
    await recorder.start(question="q", history=[])
    result = await run_tutor(
        recorder,
        plan(default=HistoryConfig(scope="baseline", on_miss="passthrough")),
        calls_tool_then_answers("get_code_example", ARGS),
    )
    assert "makeCounter" in result.output  # the real closures example


async def test_recorded_failure_replays_as_failure(live_tool_must_not_run):
    lookup = FakeLookup({(KEY, 0): recorded(None, status=NodeStatus.FAILED, error="db down")})
    recorder = recorder_for(FakeKitaru(), secrets=[])
    await recorder.start(question="q", history=[])
    with pytest.raises(RecordedToolFailure, match="db down"):
        await run_tutor(
            recorder,
            plan(default=HistoryConfig(scope="baseline", on_miss="fail"), lookup=lookup),
            calls_tool_then_answers("get_code_example", ARGS),
        )


@pytest.mark.parametrize(
    "case, args, expected",
    [
        (StaticCase(match_mode="exact", match={"topic": "closures"}, result="canned"), ARGS, "canned"),
        (StaticCase(match_mode="subset", match={"topic": "closures"}, result="canned"), ARGS, "canned"),
        (StaticCase(match_mode="exact", match={"topic": "promises"}, result="canned"), ARGS, "No static result"),
    ],
)
async def test_static_policy(live_tool_must_not_run, case, args, expected):
    recorder = recorder_for(FakeKitaru(), secrets=[])
    await recorder.start(question="q", history=[])
    result = await run_tutor(
        recorder,
        plan(tools={"get_code_example": StaticConfig(cases=[case], on_miss="error_result")}),
        calls_tool_then_answers("get_code_example", args),
    )
    assert expected in result.output


async def test_per_tool_policy_overrides_default(live_tool_must_not_run):
    """Default is passthrough, but get_code_example is pinned to a static answer."""
    recorder = recorder_for(FakeKitaru(), secrets=[])
    await recorder.start(question="q", history=[])
    result = await run_tutor(
        recorder,
        plan(
            default=PassthroughConfig(),
            tools={"get_code_example": StaticConfig(cases=[StaticCase(match_mode="subset", match={}, result="pinned")], on_miss="fail")},
        ),
        calls_tool_then_answers("get_code_example", ARGS),
    )
    assert "pinned" in result.output
