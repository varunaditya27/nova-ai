"""People routes: real PostgresSocialStore (SQLite), through the real FastAPI app."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.dependencies import get_state
from api.routes.people import router as people_router
from backend.layer5_relationship.schemas import SocialEvent, SocialGraph, SocialNode, SocialPattern
from infra.db.engine import init_db, make_session_factory
from infra.db.social_store import PostgresSocialStore

USER = "local-user"


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id=USER)
    app = FastAPI()
    app.include_router(people_router)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), PostgresSocialStore(factory)


def _seed_person(store, **kwargs):
    kwargs.setdefault("display_name", "Priya")
    kwargs.setdefault("relationship_type", "close_friend")
    kwargs.setdefault("mention_count", 3)
    node = SocialNode(**kwargs)
    graph = store.load_graph(USER) or SocialGraph(user_id=USER)
    graph.nodes[node.person_id] = node
    store.save_graph(graph)
    return node


def test_list_people_empty_when_no_graph():
    client, _ = _client()
    assert client.get("/people").json() == []


def test_list_people_sorted_by_mention_count():
    client, store = _client()
    low = _seed_person(store, display_name="Sam", mention_count=1)
    graph = store.load_graph(USER)
    graph.nodes[low.person_id] = low
    high = SocialNode(display_name="Priya", relationship_type="close_friend", mention_count=9)
    graph.nodes[high.person_id] = high
    store.save_graph(graph)

    body = client.get("/people").json()
    assert [p["display_name"] for p in body] == ["Priya", "Sam"]


def test_get_person_not_found_is_404():
    client, _ = _client()
    assert client.get("/people/does-not-exist").status_code == 404


def test_get_person_includes_timeline_and_patterns():
    client, store = _client()
    node = _seed_person(store)

    event = SocialEvent(person_id=node.person_id, event_type="conflict_onset",
                        summary="a disagreement about weekend plans")
    store.save_event(USER, event)

    pattern = SocialPattern(person_ids_involved=[node.person_id],
                            plain_language_description="tension resurfaces around plans")
    store.save_patterns(USER, [pattern])

    body = client.get(f"/people/{node.person_id}").json()
    assert body["display_name"] == "Priya"
    assert len(body["recent_events"]) == 1
    assert body["recent_events"][0]["summary"] == "a disagreement about weekend plans"
    assert len(body["active_patterns"]) == 1
    assert body["active_patterns"][0]["plain_language_description"] == "tension resurfaces around plans"


def test_get_person_excludes_other_peoples_events():
    client, store = _client()
    a = _seed_person(store, display_name="Priya")
    graph = store.load_graph(USER)
    b = SocialNode(display_name="Jordan", relationship_type="friend")
    graph.nodes[b.person_id] = b
    store.save_graph(graph)

    store.save_event(USER, SocialEvent(person_id=b.person_id, summary="about Jordan"))

    body = client.get(f"/people/{a.person_id}").json()
    assert body["recent_events"] == []
