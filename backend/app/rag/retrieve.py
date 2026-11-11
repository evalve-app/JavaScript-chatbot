"""Embeddings + exact cosine-similarity search over lesson chunks with pgvector.

When called during a recorded turn, both steps appear in the Kitaru trace, shaped like
OpenInference (Arize Phoenix) traces: a RETRIEVER span with its EMBEDDING call inside.
"""

from functools import lru_cache

from kitaru.api_models.v1.session import TokenUsage
from kitaru.api_models.v1.session_node import NodeType
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DocumentChunk
from app.recording.context import trace_step


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
    model = settings.embedding_model
    with trace_step(
        NodeType.LLM_CALL,
        f"embeddings {model}",  # OpenTelemetry GenAI span name: "{operation} {model}"
        inputs={"input": texts},
        input_text_selector="/input/0" if len(texts) == 1 else None,
        requested_model=model,
        model_provider="openai",
        attributes={
            "gen_ai.operation.name": "embeddings",
            "gen_ai.provider.name": "openai",
            "gen_ai.request.model": model,
            "openinference.span.kind": "EMBEDDING",
        },
    ) as step:
        response = _openai_client().embeddings.create(
            model=model, input=texts, dimensions=settings.embedding_dimensions
        )
        vectors = [item.embedding for item in response.data]
        # The vectors themselves are long and unreadable; record their count and size.
        step.outputs = {"embeddings": len(vectors), "dimensions": len(vectors[0]) if vectors else 0}
        input_tokens = response.usage.prompt_tokens if response.usage else None
        step.fields.update(model=response.model, tokens=TokenUsage(input_tokens=input_tokens, output_tokens=0))
        step.attributes.update(
            {
                "gen_ai.response.model": response.model,
                "gen_ai.usage.input_tokens": input_tokens,
                "gen_ai.embeddings.dimension.count": step.outputs["dimensions"],
            }
        )
    return vectors


def search_chunks(db: Session, query: str, top_k: int | None = None) -> list[LessonResult]:
    """Embed the query and return the top-k most similar chunks (no index = exact search)."""
    top_k = top_k or get_settings().rag_top_k
    with trace_step(
        NodeType.SPAN,
        "retrieve lessons",
        inputs={"query": query, "top_k": top_k},
        input_text_selector="/query",
        attributes={
            "openinference.span.kind": "RETRIEVER",
            "db.system.name": "postgresql",
            "db.operation.name": "SELECT",
            "db.collection.name": DocumentChunk.__tablename__,
            "retrieval.metric": "cosine",
            "retrieval.exact": True,
        },
    ) as step:
        query_embedding = embed_texts([query])[0]
        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
        rows = db.execute(select(DocumentChunk, distance).order_by(distance).limit(top_k)).all()
        results = [
            LessonResult(
                document_id=chunk.id,
                title=chunk.document_title,
                content=chunk.content,
                similarity=round(1 - dist, 4),
                source_filename=chunk.source_filename,
            )
            for chunk, dist in rows
        ]
        # Ids and scores only: the full text is already in the tool's output.
        step.outputs = {
            "documents": [
                {"id": r.document_id, "title": r.title, "source_filename": r.source_filename, "score": r.similarity}
                for r in results
            ]
        }
    return results
