"""Embeddings + exact cosine-similarity search over lesson chunks with pgvector."""

from functools import lru_cache

from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DocumentChunk


class LessonResult(BaseModel):
    document_id: int
    title: str
    content: str
    similarity: float
    source_filename: str


@lru_cache
def _openai_client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    response = _openai_client().embeddings.create(
        model=settings.embedding_model, input=texts, dimensions=settings.embedding_dimensions
    )
    return [item.embedding for item in response.data]


def search_chunks(db: Session, query: str, top_k: int | None = None) -> list[LessonResult]:
    """Embed the query and return the top-k most similar chunks (no index = exact search)."""
    top_k = top_k or get_settings().rag_top_k
    query_embedding = embed_texts([query])[0]
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
    rows = db.execute(select(DocumentChunk, distance).order_by(distance).limit(top_k)).all()
    return [
        LessonResult(
            document_id=chunk.id,
            title=chunk.document_title,
            content=chunk.content,
            similarity=round(1 - dist, 4),
            source_filename=chunk.source_filename,
        )
        for chunk, dist in rows
    ]
