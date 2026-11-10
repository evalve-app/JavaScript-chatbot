"""FastAPI app: HTTP handling only. Agent logic lives in app/agents/workflow.py."""

import logging
import uuid

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.agents.workflow import WorkflowError, run_chat_turn
from app.auth import clear_session_cookie, current_member, set_session_cookie
from app.database import get_db
from app.models import AgentRun, Conversation, Message, TeamMember
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    LoginRequest,
    MemberOut,
    MessageOut,
    RunDetails,
    Source,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("studybot")

# The Vite dev server proxies /api here, so the browser sees one origin and no CORS setup is needed.
app = FastAPI(title="StudyBot API")


def get_owned_conversation(db: Session, conversation_id: uuid.UUID, member: TeamMember) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    # 404 (not 403) so other teammates' conversation IDs aren't revealed.
    if conversation is None or conversation.team_member_id != member.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


# ---------- Health ----------


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return {"status": "ok", "database": database}


# ---------- Sign-in (display name only) ----------


@app.post("/api/auth/login", response_model=MemberOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> MemberOut:
    name = body.display_name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Display name is required")
    # Same display name -> same member, so a teammate sees their chats on any device.
    member = db.scalar(select(TeamMember).where(func.lower(TeamMember.display_name) == name.lower()))
    if member is None:
        member = TeamMember(display_name=name)
        db.add(member)
        db.commit()
    set_session_cookie(response, member.id)
    return MemberOut(id=member.id, display_name=member.display_name)


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.get("/api/auth/me", response_model=MemberOut)
def me(member: TeamMember = Depends(current_member)) -> MemberOut:
    return MemberOut(id=member.id, display_name=member.display_name)


# ---------- Conversations ----------


@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations(
    member: TeamMember = Depends(current_member), db: Session = Depends(get_db)
) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.team_member_id == member.id)
            .order_by(Conversation.updated_at.desc())
            .limit(100)
        )
    )


@app.post("/api/conversations", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_conversation(member: TeamMember = Depends(current_member), db: Session = Depends(get_db)) -> Conversation:
    conversation = Conversation(team_member_id=member.id, title="New chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def run_details(run: AgentRun) -> RunDetails:
    classification = None
    if run.scope and run.intent and run.language:
        classification = {"scope": run.scope, "intent": run.intent, "language": run.language}
    return RunDetails(
        request_id=run.request_id,
        classification=classification,
        route=run.selected_route,
        tools_called=run.tools_called or [],
        sources=[Source(**s) for s in run.retrieved_sources or []],
        duration_ms=run.duration_ms,
        model_name=run.model_name,
    )


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID, member: TeamMember = Depends(current_member), db: Session = Depends(get_db)
) -> ConversationDetail:
    conversation = get_owned_conversation(db, conversation_id, member)
    runs = {
        run.message_id: run
        for run in db.scalars(
            select(AgentRun).where(AgentRun.conversation_id == conversation.id, AgentRun.message_id.is_not(None))
        )
    }
    messages = [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            details=run_details(runs[m.id]) if m.id in runs else None,
        )
        for m in db.scalars(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
        )
    ]
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


# ---------- Chat ----------


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest, member: TeamMember = Depends(current_member), db: Session = Depends(get_db)
) -> ChatResponse | JSONResponse:
    if not body.message.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Message cannot be empty")
    if body.conversation_id:
        conversation = get_owned_conversation(db, body.conversation_id, member)
    else:
        conversation = Conversation(team_member_id=member.id, title="New chat")
        db.add(conversation)
        db.commit()

    try:
        result = await run_chat_turn(db, conversation, body.message)
    except WorkflowError as exc:
        logger.exception("chat turn failed (request_id=%s)", exc.request_id)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "detail": str(exc),
                "request_id": str(exc.request_id),
                "conversation_id": str(conversation.id),
            },
        )

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=result.message_id,
        request_id=result.request_id,
        response=result.response,
        classification=result.classification,
        route=result.route,
        tools_called=result.tools_called,
        sources=[Source(**s) for s in result.sources],
        duration_ms=result.duration_ms,
    )
