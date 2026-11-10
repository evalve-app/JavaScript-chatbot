"""Tool: search_lessons — RAG search over StudyBot's JavaScript lessons in Neon."""

import logging

from pydantic_ai import ModelRetry, RunContext

from app.agents.deps import TutorDeps
from app.database import new_session
from app.rag.retrieve import LessonResult, search_chunks

logger = logging.getLogger(__name__)


def search_lessons(ctx: RunContext[TutorDeps], query: str) -> list[LessonResult]:
    """Search StudyBot's JavaScript lesson library and return the most relevant passages.

    Returns an empty list if nothing is found or the library is unavailable.

    Args:
        query: What to look up, e.g. "how closures capture variables".
    """
    if not query.strip():
        raise ModelRetry("Provide a non-empty search query.")
    try:
        with new_session() as db:
            results = search_chunks(db, query)
    except Exception:
        # Don't fail the whole answer if retrieval breaks; the tutor can still answer.
        logger.exception("search_lessons failed")
        return []
    for r in results:
        ctx.deps.retrieved_sources.append({"title": r.title, "source_filename": r.source_filename})
    return results
