"""Build a TurnRecorder for the running app from settings."""

import logging
import uuid

from kitaru.client import KitaruAPIClient

from app.config import get_settings
from app.recording.capture import secret_values
from app.recording.recorder import TurnRecorder

logger = logging.getLogger(__name__)

# Short timeout and one retry: a slow or stopped Kitaru server must not hold up chat.
CLIENT_TIMEOUT_SECONDS = 5.0
CLIENT_RETRIES = 1


def kitaru_client() -> KitaruAPIClient:
    settings = get_settings()
    return KitaruAPIClient(
        base_url=settings.kitaru_api_url or None,  # None -> KITARU_API_URL or `kitaru login`
        api_key=settings.kitaru_api_key or None,
        timeout=CLIENT_TIMEOUT_SECONDS,
        retries=CLIENT_RETRIES,
    )


def agent_ids() -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """(agent_id, agent_version_id) from settings; agent_id None means recording is off."""
    settings = get_settings()
    try:
        agent_id = uuid.UUID(settings.kitaru_agent_id) if settings.kitaru_agent_id else None
        version_id = uuid.UUID(settings.kitaru_agent_version_id) if settings.kitaru_agent_version_id else None
    except ValueError:
        logger.warning("KITARU_AGENT_ID / KITARU_AGENT_VERSION_ID is not a UUID; recording is off")
        return None, None
    return agent_id, version_id


def new_turn_recorder() -> TurnRecorder:
    """A recorder for one live chat turn: disabled unless KITARU_AGENT_ID is set."""
    agent_id, _ = agent_ids()
    factory = kitaru_client if agent_id else None
    return TurnRecorder(factory, secret_values(get_settings()))
