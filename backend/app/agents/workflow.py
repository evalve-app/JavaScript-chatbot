"""Orchestration: classify -> route -> tutor (with tools) -> persist.

Independent of FastAPI: takes a DB session and plain values, returns a plain result.
"""

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
from app.agents.tutor import tutor_agent
from app.config import get_settings
from app.models import AgentRun, Conversation, Message

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


async def run_chat_turn(db: Session, conversation: Conversation, user_text: str) -> WorkflowResult:
    settings = get_settings()
    request_id = uuid.uuid4()
    started = time.perf_counter()
    model = get_chat_model()

    history = load_recent_history(db, conversation.id, settings.history_limit)

    db.add(Message(conversation_id=conversation.id, role="user", content=user_text))
    if conversation.title == "New chat":
        conversation.title = user_text.strip().splitlines()[0][:60] or "New chat"
    db.commit()

    run_log = AgentRun(request_id=request_id, conversation_id=conversation.id, model_name=settings.openai_model)
    deps: TutorDeps | None = None
    try:
        # 1. Classify scope + intent in one call.
        classification_run = await classifier_agent.run(build_classifier_input(user_text, history), model=model)
        classification = classification_run.output
        route = select_route(classification)
        run_log.scope, run_log.intent, run_log.language = (
            classification.scope,
            classification.intent,
            classification.language,
        )
        run_log.selected_route = route

        # 2. Route. Out-of-scope requests never reach RAG or the tutor.
        tools_called: list[str] = []
        if route == "out_of_scope":
            response_text = OUT_OF_SCOPE_RESPONSE
        elif route == "out_of_scope_other_language":
            response_text = OTHER_LANGUAGE_RESPONSE
        else:
            deps = TutorDeps(route=route)
            tutor_run = await tutor_agent.run(
                user_text, deps=deps, message_history=to_model_messages(history), model=model
            )
            response_text = tutor_run.output
            tools_called = tool_names_called(tutor_run.new_messages())

        sources = unique_sources(deps.retrieved_sources) if deps else []

        # 3. Persist the answer + run metadata.
        assistant_message = Message(conversation_id=conversation.id, role="assistant", content=response_text)
        db.add(assistant_message)
        db.flush()
        duration_ms = int((time.perf_counter() - started) * 1000)
        run_log.message_id = assistant_message.id
        run_log.tools_called = tools_called
        run_log.retrieved_sources = sources
        run_log.duration_ms = duration_ms
        db.add(run_log)
        conversation.updated_at = func.now()  # bump for sidebar ordering
        db.commit()
    except Exception as exc:
        db.rollback()
        run_log.duration_ms = int((time.perf_counter() - started) * 1000)
        run_log.error_message = f"{type(exc).__name__}: {exc}"[:2000]
        run_log.retrieved_sources = unique_sources(deps.retrieved_sources) if deps else []
        run_log.tools_called = []
        run_log.message_id = None
        db.add(run_log)
        db.commit()
        raise WorkflowError(request_id, "StudyBot couldn't generate a response. Please try again.") from exc

    return WorkflowResult(
        request_id=request_id,
        message_id=assistant_message.id,
        response=response_text,
        classification=classification,
        route=route,
        tools_called=tools_called,
        sources=sources,
        duration_ms=duration_ms,
    )
