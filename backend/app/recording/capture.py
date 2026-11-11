"""Turn values into bounded, secret-free JSON before they are sent to Kitaru."""

import dataclasses
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel

from app.config import Settings

MAX_STRING = 20_000  # long enough for a full lesson chunk or answer
MAX_ITEMS = 200
MAX_DEPTH = 8
MIN_SECRET_LENGTH = 8  # shorter values are too likely to appear in normal text
REDACTED = "[REDACTED]"


def secret_values(settings: Settings) -> list[str]:
    """Every configured credential, so it can be scrubbed from recorded text."""
    candidates = [settings.openai_api_key, settings.kitaru_api_key, settings.session_secret, settings.database_url]
    try:
        candidates.append(urlsplit(settings.database_url).password or "")
    except ValueError:
        pass
    # Longest first, so a password inside the URL can't break the URL's redaction.
    return sorted({c for c in candidates if c and len(c) >= MIN_SECRET_LENGTH}, key=len, reverse=True)


def redact(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        text = text.replace(secret, REDACTED)
    return text


def capture(value: Any, secrets: list[str], depth: int = 0) -> Any:
    """JSON-safe copy of value: secrets redacted, strings/collections/depth bounded."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        text = redact(value, secrets)
        if len(text) > MAX_STRING:
            return text[:MAX_STRING] + f"… [truncated {len(text) - MAX_STRING} chars]"
        return text
    if depth >= MAX_DEPTH:
        return "[max depth reached]"
    if isinstance(value, BaseModel):
        return capture(value.model_dump(mode="json"), secrets, depth + 1)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return capture(dataclasses.asdict(value), secrets, depth + 1)
    if isinstance(value, dict):
        items = list(value.items())
        result = {redact(str(k), secrets): capture(v, secrets, depth + 1) for k, v in items[:MAX_ITEMS]}
        if len(items) > MAX_ITEMS:
            result["[truncated]"] = f"{len(items) - MAX_ITEMS} more keys"
        return result
    if isinstance(value, list | tuple | set):
        items = list(value)
        result = [capture(v, secrets, depth + 1) for v in items[:MAX_ITEMS]]
        if len(items) > MAX_ITEMS:
            result.append(f"[truncated {len(items) - MAX_ITEMS} more items]")
        return result
    # Unknown objects: record the type only. str() could leak credentials or memory addresses.
    return f"[unrecordable {type(value).__name__}]"


def capture_error(error: BaseException, secrets: list[str]) -> str:
    return capture(f"{type(error).__name__}: {error}", secrets)[:2000]
