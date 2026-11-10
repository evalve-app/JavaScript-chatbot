"""Display-name sign-in: keeps each teammate's chats separate in the shared database.

There is no password. The app runs locally, and the display name only decides
whose conversations you see. Two people using the same name share a history.
"""

import uuid

from fastapi import Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import TeamMember

COOKIE_NAME = "studybot_session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="studybot-session")


def set_session_cookie(response: Response, member_id: uuid.UUID) -> None:
    response.set_cookie(
        COOKIE_NAME,
        _serializer().dumps(str(member_id)),
        max_age=get_settings().session_max_age_days * 86400,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


def current_member(request: Request, db: Session = Depends(get_db)) -> TeamMember:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    try:
        member_id = uuid.UUID(_serializer().loads(token, max_age=get_settings().session_max_age_days * 86400))
    except (BadSignature, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session") from None
    member = db.get(TeamMember, member_id)
    if member is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    return member
