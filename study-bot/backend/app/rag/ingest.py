"""Ingest Markdown lessons into Neon: chunk -> embed -> store.

Run from backend/:  uv run python -m app.rag.ingest

Re-running is safe: a document whose file hash is unchanged is skipped; a changed
document has its old chunks replaced.
"""

import hashlib
import re
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import new_session
from app.models import DocumentChunk
from app.rag.retrieve import embed_texts

LESSONS_DIR = Path(__file__).resolve().parents[2] / "data" / "lessons"
MAX_CHUNK_TOKENS = 450  # target ~300-500 tokens per chunk


def estimate_tokens(text: str) -> int:
    # ~4 characters per token for English text; precise counts aren't needed here.
    return max(1, len(text) // 4)


def extract_title(markdown: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def split_blocks(markdown: str) -> list[str]:
    """Split on blank lines, but keep fenced code blocks intact."""
    blocks, current, in_code = [], [], False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        if not line.strip() and not in_code:
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def chunk_markdown(markdown: str, max_tokens: int = MAX_CHUNK_TOKENS) -> list[str]:
    """Group blocks into chunks, starting a new chunk at a heading once the current one is substantial."""
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for block in split_blocks(markdown):
        block_tokens = estimate_tokens(block)
        is_heading = block.startswith("## ")
        too_big = current_tokens + block_tokens > max_tokens
        heading_break = is_heading and current_tokens > max_tokens * 0.6
        if current and (too_big or heading_break):
            chunks.append("\n\n".join(current))
            current, current_tokens = [], 0
        current.append(block)
        current_tokens += block_tokens
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def ingest_file(db: Session, path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    file_hash = hashlib.sha256(text.encode()).hexdigest()
    existing_hash = db.scalar(
        select(DocumentChunk.content_hash).where(DocumentChunk.source_filename == path.name).limit(1)
    )
    if existing_hash == file_hash:
        return "skipped"

    title = extract_title(text, path.stem)
    chunks = chunk_markdown(text)
    # Prefix the title so every chunk's embedding knows which topic it belongs to.
    embeddings = embed_texts([f"{title}\n\n{chunk}" for chunk in chunks])

    db.execute(delete(DocumentChunk).where(DocumentChunk.source_filename == path.name))
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        db.add(
            DocumentChunk(
                document_title=title,
                source_filename=path.name,
                chunk_index=index,
                content=chunk,
                content_hash=file_hash,
                embedding=embedding,
            )
        )
    db.commit()
    return "updated" if existing_hash else "added"


def ingest_all(lessons_dir: Path = LESSONS_DIR) -> dict[str, str]:
    results = {}
    with new_session() as db:
        for path in sorted(lessons_dir.glob("*.md")):
            results[path.name] = ingest_file(db, path)
    return results


if __name__ == "__main__":
    for filename, status in ingest_all().items():
        print(f"{status:8} {filename}")
