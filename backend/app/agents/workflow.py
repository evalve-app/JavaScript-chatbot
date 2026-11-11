"""Orchestration: classify -> route -> tutor (with tools), recorded to Kitaru when enabled.

Two layers, both independent of FastAPI:
- answer_turn():   the agent work only. No database writes, so Kitaru replays can reuse it.
- run_chat_turn(): the live app. Loads history, saves messages + agent_runs, records the turn.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.classifier import Classification, build_classifier_input, classifier_agent
from app.agents.deps import TutorDeps
from app.agents.models import get_chat_model
from app.agents.prompts import OTHER_LANGUAGE_RESPONSE, OUT_OF_SCOPE_RESPONSE
from app.agents.tutor import tutor_agent, tutor_prompt_override
from app.config import get_settings
from app.models import AgentRun, Conversation, Message
from app.recording.hooks import RecordingHooks
from app.recording.live import agent_ids, new_turn_recorder
from app.recording.recorder import TurnRecorder
from app.recording.replay import ReplayPlan

logger = logging.getLogger(__name__)

MAX_HISTORY_CHARS = 2000  # per message, to keep token costs predictable


@dataclass
class WorkflowResult:
    request_id: uuid.UUID
    message_id: uuid.UUID
    response: str
    classification: Classification
    route: str
    tools_called: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    duration_ms: int = 0
    kitaru_status: str = "disabled"
    kitaru_session_id: uuid.UUID | None = None


class WorkflowError(Exception):
    def __init__(self, request_id: uuid.UUID, message: str):
        super().__init__(message)
        self.request_id = request_id


def select_route(classification: Classification) -> str:
    if classification.scope == "out_of_scope":
        return "out_of_scope_other_language" if classification.language == "other" else "out_of_scope"
    return classification.intent


def load_recent_history(db: Session, conversation_id: uuid.UUID, limit: int) -> list[tuple[str, str]]:
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    return [(m.role, m.content) for m in reversed(rows)]


def to_model_messages(history: list[tuple[str, str]]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for role, content in history:
        content = content[:MAX_HISTORY_CHARS]
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


def tool_names_called(messages: list[ModelMessage]) -> list[str]:
    return [
        part.tool_name
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart)
    ]


def unique_sources(sources: list[dict]) -> list[dict]:
    seen, result = set(), []
    for s in sources:
        if s["source_filename"] not in seen:
            seen.add(s["source_filename"])
            result.append(s)
    return result


@dataclass
class TurnAnswer:
    """What answer_turn produced. Filled step by step, so a failure still shows how far it got."""

    question: str
    classification: Classification | None = None
    route: str | None = None
    response: str | None = None
    tools_called: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)


class TurnFailed(Exception):
    """answer_turn failed; .partial holds the steps that finished."""

    def __init__(self, partial: TurnAnswer):
        super().__init__("turn failed")
        self.partial = partial


async def answer_turn(
    question: str,
    history: list[tuple[str, str]],
    *,
    recorder: TurnRecorder | None = None,
    replay: ReplayPlan | None = None,
) -> TurnAnswer:
    """Classify, route, and (for JavaScript questions) run the tutor. No database writes."""
    recorder = recorder or TurnRecorder(None, [])
    override = replay.override if replay else None
    if override and override.prompt:
        question = override.prompt  # Kitaru "prompt" override: a different question, same history
    model = get_chat_model()
    answer = TurnAnswer(question=question)
    span = None
    try:
        # 1. Classify scope + intent in one call.
        span = recorder.begin_span("classify", inputs={"question": question})
        hooks = RecordingHooks(recorder, span, "classifier", replay=replay)
        result = await classifier_agent.run(
            build_classifier_input(question, history), model=model, capabilities=[hooks]
        )
        answer.classification = result.output
        answer.route = select_route(answer.classification)
        recorder.end_span(span, outputs={**answer.classification.model_dump(), "route": answer.route})

        # 2. Route. Out-of-scope requests never reach RAG or the tutor.
        if answer.route == "out_of_scope":
            answer.response = OUT_OF_SCOPE_RESPONSE
        elif answer.route == "out_of_scope_other_language":
            answer.response = OTHER_LANGUAGE_RESPONSE
        else:
            span = recorder.begin_span("tutor", inputs={"route": answer.route})
            deps = TutorDeps(route=answer.route)
            hooks = RecordingHooks(recorder, span, "tutor", replay=replay)
            try:
                with tutor_prompt_override(override.system_prompt if override else None):
                    result = await tutor_agent.run(
                        question,
                        deps=deps,
                        message_history=to_model_messages(history),
                        model=model,
                        capabilities=[hooks],
                    )
            finally:
                answer.sources = unique_sources(deps.retrieved_sources)
            answer.response = result.output
            answer.tools_called = tool_names_called(result.new_messages())
            recorder.end_span(span, outputs={"answer": answer.response})
    except Exception as exc:
        if span is not None:
            recorder.end_span(span, error=exc)
        raise TurnFailed(answer) from exc
    return answer


async def run_chat_turn(db: Session, conversation: Conversation, user_text: str) -> WorkflowResult:
    settings = get_settings()
    request_id = uuid.uuid4()
    started = time.perf_counter()

    history = load_recent_history(db, conversation.id, settings.history_limit)

    db.add(Message(conversation_id=conversation.id, role="user", content=user_text))
    if conversation.title == "New chat":
        conversation.title = user_text.strip().splitlines()[0][:60] or "New chat"
    db.commit()

    recorder = new_turn_recorder()
    agent_id, agent_version_id = agent_ids()
    await recorder.start(
        question=user_text,
        history=history,
        agent_id=agent_id,
        agent_version_id=agent_version_id,
        metadata={"source": "studybot-web", "request_id": str(request_id), "conversation_id": str(conversation.id)},
    )

    run_log = AgentRun(request_id=request_id, conversation_id=conversation.id, model_name=settings.openai_model)
    try:
        answer = await answer_turn(user_text, history, recorder=recorder)
    except TurnFailed as failed:
        error = failed.__cause__ or failed
        await recorder.finish(error=error)
        _log_kitaru(recorder, request_id)
        _fill_run_log(run_log, failed.partial, recorder)
        db.rollback()
        run_log.duration_ms = int((time.perf_counter() - started) * 1000)
        run_log.error_message = f"{type(error).__name__}: {error}"[:2000]
        run_log.tools_called = []
        db.add(run_log)
        db.commit()
        raise WorkflowError(request_id, "StudyBot couldn't generate a response. Please try again.") from error

    await recorder.finish(answer=answer.response)
    _log_kitaru(recorder, request_id)

    # Persist the answer + run metadata.
    assistant_message = Message(conversation_id=conversation.id, role="assistant", content=answer.response)
    db.add(assistant_message)
    db.flush()
    duration_ms = int((time.perf_counter() - started) * 1000)
    _fill_run_log(run_log, answer, recorder)
    run_log.message_id = assistant_message.id
    run_log.duration_ms = duration_ms
    db.add(run_log)
    conversation.updated_at = func.now()  # bump for sidebar ordering
    db.commit()

    return WorkflowResult(
        request_id=request_id,
        message_id=assistant_message.id,
        response=answer.response,
        classification=answer.classification,
        route=answer.route,
        tools_called=answer.tools_called,
        sources=answer.sources,
        duration_ms=duration_ms,
        kitaru_status=recorder.outcome.value,
        kitaru_session_id=recorder.session_id,
    )


def _fill_run_log(run_log: AgentRun, answer: TurnAnswer, recorder: TurnRecorder) -> None:
    run_log.kitaru_status = recorder.outcome.value
    run_log.kitaru_session_id = recorder.session_id
    run_log.kitaru_problem = recorder.problem
    if answer.classification is not None:
        c = answer.classification
        run_log.scope, run_log.intent, run_log.language = c.scope, c.intent, c.language
    run_log.selected_route = answer.route
    run_log.tools_called = answer.tools_called
    run_log.retrieved_sources = answer.sources


def _log_kitaru(recorder: TurnRecorder, request_id: uuid.UUID) -> None:
    if recorder.problem:
        logger.warning("Kitaru %s for request %s: %s", recorder.outcome, request_id, recorder.problem)
