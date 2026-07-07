"""Conversation-log + continuity routes: history, search, bookmarks, milestones, home, calendar."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.dependencies import get_state
from api.routes.messages import router as messages_router
from api.routes.continuity import router as continuity_router
from infra.db.engine import make_session_factory, init_db
from infra.db.message_store import PostgresMessageStore


def _client():
    # StaticPool + check_same_thread=False so the FastAPI worker thread sees the seeded in-memory DB.
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user",
                            config={"onboarding": {"graduation_sessions": 5}},
                            vector_store=None, llm_clients={})
    app = FastAPI()
    app.include_router(messages_router)
    app.include_router(continuity_router)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), PostgresMessageStore(factory, "local-user")


def test_history_returns_messages_newest_first_with_echoes():
    client, store = _client()
    store.append("user", "hey")
    store.append("nova", "hello", echoes=[{"summary": "you mentioned Mongo", "created_at": None}])
    body = client.get("/messages").json()
    assert [m["role"] for m in body] == ["nova", "user"]
    assert body[0]["echoes"][0]["summary"] == "you mentioned Mongo"


def test_history_pagination_uses_exposed_cursor():
    client, store = _client()
    for i in range(4):
        store.append("user", f"m{i}")
    page1 = client.get("/messages", params={"limit": 2}).json()
    assert [x["content"] for x in page1] == ["m3", "m2"]
    cursor = page1[-1]["cursor"]                     # frontend pages back with the last item's cursor
    assert cursor > 0
    page2 = client.get("/messages", params={"limit": 2, "before": cursor}).json()
    assert [x["content"] for x in page2] == ["m1", "m0"]


def test_keyword_search_endpoint():
    client, store = _client()
    store.append("user", "the hackathon was wild")
    store.append("user", "nothing special")
    hits = client.get("/messages/search", params={"q": "hackathon"}).json()
    assert len(hits) == 1 and "hackathon" in hits[0]["content"]


def test_bookmark_flow():
    client, store = _client()
    mid = store.append("user", "keep this")
    r = client.post(f"/messages/{mid}/bookmark", json={"category": "Idea"})
    assert r.status_code == 200 and r.json()["bookmarked"] is True
    assert client.get("/bookmarks").json()[0]["bookmark_category"] == "Idea"
    assert client.delete(f"/messages/{mid}/bookmark").json()["bookmarked"] is False
    assert client.get("/bookmarks").json() == []


def test_bookmark_missing_is_404():
    client, _ = _client()
    assert client.post("/messages/nope/bookmark", json={}).status_code == 404


def test_milestone_flow():
    client, store = _client()
    mid = store.append("user", "we launched")
    assert client.post(f"/messages/{mid}/milestone", json={"label": "Launch"}).status_code == 200
    ms = client.get("/milestones").json()
    assert len(ms) == 1 and ms[0]["milestone_label"] == "Launch"


def test_home_desk():
    client, store = _client()
    store.append("user", "hi")
    body = client.get("/home").json()
    assert body["greeting"].startswith("Good ")
    assert body["message_count"] == 1
    assert body["relationship_stage"] == "new"
    assert body["weather"] in {"sunny", "clear", "cloudy", "distant"}


def test_calendar_and_museum():
    client, store = _client()
    store.append("user", "first ever message")
    cal = client.get("/calendar").json()
    assert isinstance(cal["days"], dict) and sum(cal["days"].values()) >= 1
    museum = client.get("/museum").json()
    assert any(e["label"] == "First conversation" for e in museum["entries"])
