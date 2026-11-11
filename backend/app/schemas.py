"""Pydantic request/response models for the HTTP API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)


class MemberOut(BaseModel):
    id: uuid.UUID
    display_name: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: uuid.UUID | None = None


class Source(BaseModel):
    title: str
    source_filename: str


class RunDetails(BaseModel):
    """Developer details shown under each assistant message."""

    request_id: uuid.UUID
    tools_called: list[str]
    sources: list[Source]
    duration_ms: int
    model_name: str
    kitaru_status: str | None = None
    kitaru_session_id: uuid.UUID | None = None
    kitaru_problem: str | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    request_id: uuid.UUID
    response: str
    tools_called: list[str]
    sources: list[Source]
    duration_ms: int
    kitaru_status: str
    kitaru_session_id: uuid.UUID | None = None


class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    details: RunDetails | None = None


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut]
