import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import login
from tests.fakes import fake_agents


# ---------- Sign-in ----------


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/conversations"),
        ("post", "/api/conversations"),
        ("get", f"/api/conversations/{uuid.uuid4()}"),
        ("get", "/api/auth/me"),
    ],
)
def test_endpoints_require_session(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_chat_requires_session(client):
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 401


def test_login_sets_httponly_cookie_and_me_works(client):
    response = client.post("/api/auth/login", json={"display_name": "Ana"})
    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert "studybot_session=" in set_cookie and "HttpOnly" in set_cookie
    assert client.get("/api/auth/me").json()["display_name"] == "Ana"


def test_tampered_cookie_rejected(client):
    login(client)
    real = client.cookies.get("studybot_session")
    client.cookies.clear()
    client.cookies.set("studybot_session", real[:-3] + "abc")  # break the signature
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client):
    login(client)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_same_display_name_reuses_member(client):
    first = login(client, "Ana").get("/api/auth/me").json()["id"]
    other = login(TestClient(app), "ana").get("/api/auth/me").json()["id"]
    assert first == other


# ---------- Validation ----------


@pytest.mark.parametrize(
    "body",
    [{}, {"message": ""}, {"message": "   "}, {"message": "hi", "conversation_id": "not-a-uuid"}, {"message": "x" * 8001}],
)
def test_chat_validation(client, body):
    login(client)
    assert client.post("/api/chat", json=body).status_code == 422


@pytest.mark.parametrize("body", [{}, {"display_name": ""}, {"display_name": "   "}, {"display_name": "x" * 51}])
def test_login_validation(client, body):
    assert client.post("/api/auth/login", json=body).status_code == 422


# ---------- Chat + persistence ----------


def test_chat_creates_conversation_and_persists(client, ingested_lessons):
    login(client)
    with fake_agents(tool_calls=[("search_lessons", {"query": "closures"})], answer="A closure is..."):
        response = client.post("/api/chat", json={"message": "Explain JavaScript closures", "conversation_id": None})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["response"] == "A closure is..."
    assert "classification" not in data and "route" not in data
    assert data["tools_called"] == ["search_lessons"]
    assert any(s["source_filename"] == "04-javascript-closures.md" for s in data["sources"])
    assert data["duration_ms"] >= 0
    assert data["kitaru_status"] == "disabled" and data["kitaru_session_id"] is None

    conversations = client.get("/api/conversations").json()
    assert [c["id"] for c in conversations] == [data["conversation_id"]]
    assert conversations[0]["title"] == "Explain JavaScript closures"

    detail = client.get(f"/api/conversations/{data['conversation_id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    details = detail["messages"][1]["details"]
    assert details["request_id"] == data["request_id"]
    assert details["tools_called"] == ["search_lessons"]
    assert details["kitaru_status"] == "disabled"
    assert detail["messages"][0]["details"] is None


def test_continue_conversation(client):
    login(client)
    with fake_agents(answer="one"):
        conv_id = client.post("/api/chat", json={"message": "Explain closures"}).json()["conversation_id"]
    with fake_agents(answer="two"):
        second = client.post("/api/chat", json={"message": "Another example?", "conversation_id": conv_id})
    assert second.json()["conversation_id"] == conv_id
    messages = client.get(f"/api/conversations/{conv_id}").json()["messages"]
    assert [m["content"] for m in messages] == ["Explain closures", "one", "Another example?", "two"]


def test_create_empty_conversation(client):
    login(client)
    response = client.post("/api/conversations")
    assert response.status_code == 201
    assert response.json()["title"] == "New chat"


def test_teammates_cannot_see_each_others_conversations(client):
    ana = login(client, "Ana")
    ben = login(TestClient(app), "Ben")
    with fake_agents():
        ana_conv = ana.post("/api/chat", json={"message": "Ana's question"}).json()["conversation_id"]

    assert ben.get("/api/conversations").json() == []
    assert ben.get(f"/api/conversations/{ana_conv}").status_code == 404
    with fake_agents():
        assert ben.post("/api/chat", json={"message": "hijack", "conversation_id": ana_conv}).status_code == 404
    assert len(ana.get(f"/api/conversations/{ana_conv}").json()["messages"]) == 2


def test_chat_failure_returns_502_with_request_id(client):
    from pydantic_ai.models.function import FunctionModel

    from app.agents.tutor import tutor_agent

    def broken(messages, info):
        raise RuntimeError("OpenAI is down")

    login(client)
    with tutor_agent.override(model=FunctionModel(broken)):
        response = client.post("/api/chat", json={"message": "Explain closures"})
    assert response.status_code == 502
    body = response.json()
    assert body["request_id"] and body["conversation_id"]
    assert "OpenAI is down" not in body["detail"]  # internal errors aren't leaked
