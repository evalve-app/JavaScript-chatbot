"""Hooks on the real StudyBot agents (fake models, fake Kitaru): what lands in the session tree."""

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import app.recording.recorder as rec
from app.agents.classifier import Classification, classifier_agent
from app.agents.deps import TutorDeps
from app.agents.tutor import tutor_agent
from app.recording.hooks import RecordingHooks
from tests.fakes import fake_classifier_model, scripted_tutor_model
from tests.test_recording import FakeKitaru, only_session, recorder_for

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def no_backoff():
    rec.reset_backoff()
    yield
    rec.reset_backoff()


def nodes_by_name(session):
    return {n.name: n for n in session["nodes"].values()}


async def test_classifier_and_tutor_land_under_their_spans(ingested_lessons):
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="Explain closures", history=[])

    span = recorder.begin_span("classify", inputs={"question": "Explain closures"})
    with classifier_agent.override(model=fake_classifier_model("in_scope", "concept", "javascript")):
        result = await classifier_agent.run(
            "Explain closures", capabilities=[RecordingHooks(recorder, span, "classifier")]
        )
    recorder.end_span(span, outputs={**result.output.model_dump(), "route": "concept"})

    span = recorder.begin_span("tutor", inputs={"route": "concept"})
    tutor_model = scripted_tutor_model([("search_lessons", {"query": "closures"})], "Closures remember.")
    with tutor_agent.override(model=tutor_model):
        answer = await tutor_agent.run(
            "Explain closures",
            deps=TutorDeps(route="concept"),
            capabilities=[RecordingHooks(recorder, span, "tutor")],
        )
    recorder.end_span(span, outputs={"answer": answer.output})
    await recorder.finish(answer=answer.output)

    # Recording didn't change what the agents returned.
    assert result.output == Classification(scope="in_scope", intent="concept", language="javascript")
    assert answer.output == "Closures remember."

    s = only_session(fake)
    nodes = list(s["nodes"].values())
    classify = next(n for n in nodes if n.name == "classify")
    tutor = next(n for n in nodes if n.name == "tutor")
    assert classify.status.value == tutor.status.value == "completed"
    assert classify.outputs["route"] == "concept"

    classifier_calls = [n for n in nodes if n.name == "classifier.model_request"]
    assert len(classifier_calls) == 1
    assert classifier_calls[0].parent_external_id == classify.external_id
    assert classifier_calls[0].node_type.value == "llm_call"
    assert "You classify messages sent to StudyBot" in classifier_calls[0].inputs["instructions"]
    assert classifier_calls[0].system_prompt_selector == "/instructions"

    tutor_calls = [n for n in nodes if n.name == "tutor.model_request"]
    tools = [n for n in nodes if n.node_type.value == "tool_call"]
    assert len(tutor_calls) == 2 and len(tools) == 1
    assert all(n.parent_external_id == tutor.external_id for n in tutor_calls + tools)
    assert "You are StudyBot" in tutor_calls[0].inputs["instructions"]
    assert tutor_calls[0].inputs["messages"][0]["parts"][0]["content"] == "Explain closures"
    assert tutor_calls[-1].outputs["text"] == "Closures remember."
    assert tutor_calls[-1].tokens is not None

    tool = tools[0]
    assert tool.tool_name == "search_lessons" and tool.inputs == {"query": "closures"}
    # Full lesson text is recorded (user's choice), not a preview.
    assert len(tool.outputs) == 3
    first = tool.outputs[0]
    assert first["source_filename"] == "04-javascript-closures.md"
    from sqlalchemy import select

    from app.database import new_session
    from app.models import DocumentChunk

    with new_session() as db:
        stored = db.scalar(select(DocumentChunk.content).where(DocumentChunk.id == first["document_id"]))
    assert first["content"] == stored


async def test_failing_tool_is_recorded_and_error_still_raised():
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    span = recorder.begin_span("tutor")

    def respond(messages, info: AgentInfo):
        return ModelResponse(parts=[ToolCallPart("get_mock_progress", {"student_id": "student-001"})])

    import app.tools.progress as progress

    original = progress.new_session

    def broken_session():
        raise RuntimeError("database down")

    progress.new_session = broken_session
    try:
        with tutor_agent.override(model=FunctionModel(respond)):
            with pytest.raises(RuntimeError, match="database down"):
                await tutor_agent.run(
                    "progress?", deps=TutorDeps(route="concept"), capabilities=[RecordingHooks(recorder, span, "tutor")]
                )
    finally:
        progress.new_session = original

    await recorder.finish(error=RuntimeError("database down"))
    nodes = list(only_session(fake)["nodes"].values())
    tool = next(n for n in nodes if n.node_type.value == "tool_call")
    assert tool.status.value == "failed" and "database down" in tool.error
    span_node = next(n for n in nodes if n.name == "tutor")
    assert span_node.status.value == "failed"  # left open by the crash, closed as failed at finish


async def test_failing_model_call_is_recorded():
    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="q", history=[])
    span = recorder.begin_span("classify")

    def broken(messages, info):
        raise ConnectionError("OpenAI unreachable")

    with classifier_agent.override(model=FunctionModel(broken)):
        with pytest.raises(ConnectionError):
            await classifier_agent.run("q", capabilities=[RecordingHooks(recorder, span, "classifier")])
    recorder.end_span(span, error=ConnectionError("OpenAI unreachable"))
    await recorder.finish(error=ConnectionError("OpenAI unreachable"))

    call = nodes_by_name(only_session(fake))["classifier.model_request"]
    assert call.status.value == "failed" and "OpenAI unreachable" in call.error


async def test_hooks_with_disabled_recorder_change_nothing():
    from app.recording.recorder import TurnRecorder

    recorder = TurnRecorder(None, [])
    with classifier_agent.override(model=fake_classifier_model("out_of_scope", "concept", "unknown")):
        result = await classifier_agent.run("pizza?", capabilities=[RecordingHooks(recorder, "x", "classifier")])
    assert result.output.scope == "out_of_scope"


async def test_history_messages_are_projected_in_model_inputs():
    from pydantic_ai.messages import ModelRequest, UserPromptPart

    fake = FakeKitaru()
    recorder = recorder_for(fake, secrets=[])
    await recorder.start(question="another?", history=[("user", "closures?"), ("assistant", "A closure...")])
    span = recorder.begin_span("tutor")
    history = [
        ModelRequest(parts=[UserPromptPart(content="closures?")]),
        ModelResponse(parts=[TextPart(content="A closure...")]),
    ]
    with tutor_agent.override(model=scripted_tutor_model(answer="Here's another")):
        await tutor_agent.run(
            "another?",
            deps=TutorDeps(route="concept"),
            message_history=history,
            capabilities=[RecordingHooks(recorder, span, "tutor")],
        )
    recorder.end_span(span)
    await recorder.finish(answer="Here's another")

    call = nodes_by_name(only_session(fake))["tutor.model_request"]
    kinds = [(m["kind"], m["parts"][0]["type"]) for m in call.inputs["messages"]]
    assert kinds == [("request", "user-prompt"), ("response", "text"), ("request", "user-prompt")]
    # The selector points at the NEW question, not the old one.
    assert call.input_text_selector == "/messages/2/parts/0/content"
