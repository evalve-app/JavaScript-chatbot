from sqlalchemy import func, select

from app.models import DocumentChunk
from app.rag.ingest import LESSONS_DIR, chunk_markdown, estimate_tokens, extract_title, ingest_all
from app.rag.retrieve import search_chunks


def test_lessons_have_required_sections():
    files = sorted(LESSONS_DIR.glob("*.md"))
    assert len(files) == 22  # 15 JavaScript concept lessons + 7 PEDAC guides
    for path in files:
        text = path.read_text()
        assert text.startswith("# "), path.name
        assert "## Common Mistakes" in text, path.name
        if "-javascript-" in path.name:
            assert "```javascript" in text, path.name


def test_chunks_stay_within_target_size_and_keep_code_blocks_whole():
    for path in LESSONS_DIR.glob("*.md"):
        for chunk in chunk_markdown(path.read_text()):
            assert estimate_tokens(chunk) <= 650, (path.name, estimate_tokens(chunk))
            assert chunk.count("```") % 2 == 0, path.name


def test_extract_title():
    assert extract_title("# JavaScript Closures\n\ntext", "fallback") == "JavaScript Closures"
    assert extract_title("no heading", "fallback") == "fallback"


def test_ingestion_stores_chunks_and_is_idempotent(db):
    first = ingest_all()
    assert set(first.values()) == {"added"}
    count = db.scalar(select(func.count()).select_from(DocumentChunk))
    assert count >= 15

    second = ingest_all()
    assert set(second.values()) == {"skipped"}
    assert db.scalar(select(func.count()).select_from(DocumentChunk)) == count


def test_changed_document_is_replaced(db, tmp_path):
    lesson = tmp_path / "demo.md"
    lesson.write_text("# Demo\n\nFirst version about closures.")
    assert ingest_all(tmp_path) == {"demo.md": "added"}
    lesson.write_text("# Demo\n\nSecond version about promises.")
    assert ingest_all(tmp_path) == {"demo.md": "updated"}
    rows = db.scalars(select(DocumentChunk).where(DocumentChunk.source_filename == "demo.md")).all()
    assert len(rows) == 1 and "Second version" in rows[0].content


def test_retrieval_returns_top_three_relevant_chunks(db, ingested_lessons):
    results = search_chunks(db, "closure private state counter function factory outer variables")
    assert len(results) == 3
    assert results[0].source_filename == "04-javascript-closures.md"
    assert results[0].title == "JavaScript Closures"
    assert results[0].similarity >= results[1].similarity >= results[2].similarity
    assert all(r.document_id and r.content for r in results)
