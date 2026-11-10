"""Test setup: a real local PostgreSQL + pgvector database, fake OpenAI calls.

Set TEST_DATABASE_URL to point at your test database
(default: postgresql+psycopg:///studybot_test on the local socket).
Never point it at Neon production: tables are dropped and recreated.
"""

import hashlib
import math
import os
import re

# Configure settings BEFORE importing the app.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg:///studybot_test")
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["SESSION_SECRET"] = "test-session-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, create_tables, get_engine, new_session
from app.models import EMBEDDING_DIMENSIONS


def fake_embed_texts(texts: list[str]) -> list[list[float]]:
    """Deterministic bag-of-words hashing embedding: similar words -> similar vectors."""
    vectors = []
    for t in texts:
        vec = [0.0] * EMBEDDING_DIMENSIONS
        for word in re.findall(r"[a-z]+", t.lower()):
            if len(word) < 3:
                continue
            index = int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIMENSIONS
            vec[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        vectors.append([v / norm for v in vec] if any(vec) else [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1))
    return vectors


@pytest.fixture(scope="session", autouse=True)
def database():
    engine = get_engine()
    if "neon.tech" in str(engine.url):
        pytest.exit("Refusing to run tests against Neon. Set TEST_DATABASE_URL to a local database.")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.exit(f"Test database unavailable ({engine.url}): {exc}")
    import app.models  # noqa: F401

    Base.metadata.drop_all(engine)
    create_tables()
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "TRUNCATE agent_runs, messages, conversations, team_members, "
                "document_chunks, mock_student_progress RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    import app.rag.ingest
    import app.rag.retrieve

    monkeypatch.setattr(app.rag.retrieve, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(app.rag.ingest, "embed_texts", fake_embed_texts)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def db():
    session = new_session()
    yield session
    session.close()


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def login(client: TestClient, name: str = "Ana") -> TestClient:
    response = client.post("/api/auth/login", json={"display_name": name})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def ingested_lessons():
    from app.rag.ingest import ingest_all

    return ingest_all()


@pytest.fixture
def seeded_students():
    from app.seed import seed_students

    return seed_students()
