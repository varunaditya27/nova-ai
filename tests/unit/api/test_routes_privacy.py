"""Layer-12 over HTTP: single-memory deletion (genuine forget + certificate) and integrity."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from infra.db.engine import make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from infra.db.privacy_audit import PostgresPrivacyAudit
from backend.layer2_memory.schemas import EpisodicMemory
from api.dependencies import get_state
from api.routes.memory import router as memory_router
from api.routes.privacy import router as privacy_router


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user", config={})
    app = FastAPI()
    app.include_router(memory_router)
    app.include_router(privacy_router)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), factory


def test_delete_memory_forgets_and_certifies():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="secret thing", embedding=[0.1, 0.2])
    store.save_episodic(mem)

    resp = client.delete(f"/memory/{mem.memory_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] == 1 and body["certificate"]
    # The DELETE route now genuinely wires semantic + longitudinal cascade checks (2026-08-09
    # follow-up) -- with none referencing this episode, the cascade must say so plainly.
    assert "Nothing else" in body["cascade"]

    # Genuinely forgotten: gone from the active set and unrecallable (embedding cleared).
    assert store.active_episodic("local-user") == []
    gone = store.get_episodic(mem.memory_id)
    assert gone.is_deleted is True and (gone.embedding in (None, []))
    assert gone.summary == ""


def test_delete_memory_reports_a_real_semantic_cascade():
    """dry_run_deletion's semantic-facts cascade check read field names (fact_id/fact_text/
    derived_from_episodes) that don't exist on Layer 2's real SemanticMemory schema -- would have
    raised AttributeError the first time a real semantic_store was passed in. Proves the fix end
    to end through the live DELETE route: a semantic fact whose ONLY supporting episode is the one
    being deleted is correctly reported as "will be deleted" too."""
    from backend.layer2_memory.schemas import SemanticMemory

    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="loves hiking", embedding=[0.1, 0.2])
    store.save_episodic(mem)
    store.save_semantic(SemanticMemory(
        user_id="local-user", statement="enjoys the outdoors",
        supporting_episode_ids=[mem.memory_id]))

    resp = client.delete(f"/memory/{mem.memory_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "1 inferred fact" in body["cascade"]

    # A tamper-evident privacy-audit entry was appended.
    audit = PostgresPrivacyAudit(factory, "local-user")
    assert audit.verify() is True
    assert any(e["action"] == "delete_memory" for e in audit.entries())


def test_delete_memory_redacts_a_fact_left_with_zero_support():
    """Product decision 2026-08-09: cascade impact is now actually mutated (redact in place), not
    just reported. A fact whose only supporting episode is the deleted one must come out
    deprecated with its statement cleared and the dangling reference stripped."""
    from backend.layer2_memory.schemas import SemanticMemory

    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="loves hiking", embedding=[0.1, 0.2])
    store.save_episodic(mem)
    fact = SemanticMemory(user_id="local-user", statement="enjoys the outdoors",
                          supporting_episode_ids=[mem.memory_id])
    store.save_semantic(fact)

    resp = client.delete(f"/memory/{mem.memory_id}")
    assert resp.status_code == 200

    redacted = store.get_semantic(fact.memory_id)
    assert redacted.is_deprecated is True
    assert redacted.statement == ""
    assert redacted.supporting_episode_ids == []
    # Deprecated facts drop out of the active set entirely.
    assert redacted.memory_id not in {f.memory_id for f in store.active_semantic("local-user")}


def test_delete_memory_keeps_fact_alive_when_other_support_remains():
    """A fact with a second, undeleted supporting episode must survive with the reference to the
    deleted one stripped -- not deprecated."""
    from backend.layer2_memory.schemas import SemanticMemory

    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem1 = EpisodicMemory(user_id="local-user", summary="loves hiking", embedding=[0.1, 0.2])
    mem2 = EpisodicMemory(user_id="local-user", summary="went camping", embedding=[0.1, 0.2])
    store.save_episodic(mem1)
    store.save_episodic(mem2)
    fact = SemanticMemory(user_id="local-user", statement="enjoys the outdoors",
                          supporting_episode_ids=[mem1.memory_id, mem2.memory_id])
    store.save_semantic(fact)

    assert client.delete(f"/memory/{mem1.memory_id}").status_code == 200

    kept = store.get_semantic(fact.memory_id)
    assert kept.is_deprecated is False
    assert kept.statement == "enjoys the outdoors"
    assert kept.supporting_episode_ids == [mem2.memory_id]


def test_deleted_memory_unrecallable_via_keyword_search():
    """The keyword-scan fallback in GET /memory/search is the one path that would leak a
    deleted memory's original text if the summary field weren't actually zeroed on delete."""
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="a very particular secret phrase",
                         embedding=[0.1, 0.2])
    store.save_episodic(mem)

    assert client.get("/memory/search?q=particular+secret").json() != []
    assert client.delete(f"/memory/{mem.memory_id}").status_code == 200
    assert client.get("/memory/search?q=particular+secret").json() == []


def test_delete_missing_memory_is_404():
    client, _ = _client()
    assert client.delete("/memory/00000000-0000-0000-0000-000000000000").status_code == 404


def test_double_delete_is_404():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="x", embedding=[0.1])
    store.save_episodic(mem)
    assert client.delete(f"/memory/{mem.memory_id}").status_code == 200
    assert client.delete(f"/memory/{mem.memory_id}").status_code == 404


def test_get_deleted_memory_is_404():
    """A forgotten memory must read as not-found via GET, not return a zeroed 200 — get_episodic
    returns raw rows (Layer-12 deletion needs them), so the route must honor is_deleted."""
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="secret", embedding=[0.1, 0.2])
    store.save_episodic(mem)
    assert client.get(f"/memory/{mem.memory_id}").status_code == 200      # present before delete
    assert client.delete(f"/memory/{mem.memory_id}").status_code == 200
    assert client.get(f"/memory/{mem.memory_id}").status_code == 404      # forgotten → not found


def test_audit_full_reports_labels_facts_and_counts():
    from backend.layer2_memory.schemas import IdentityMemory, SemanticMemory
    from backend.layer7_goals.schemas import Goal, GoalStatus
    from backend.layer11_safety.schemas import CrisisSignal, CrisisTier
    from infra.db.goal_store import PostgresGoalStore
    from infra.db.safety_store import PostgresSafetyLog

    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="a big move", importance_score=0.9)
    store.save_episodic(mem)
    store.save_semantic(SemanticMemory(user_id="local-user", statement="values independence",
                                       supporting_episode_ids=[mem.memory_id], confidence=0.8))
    store.save_identity(IdentityMemory(statement="Nova values honesty", is_immutable=True))
    PostgresGoalStore(factory, "local-user").add_goal(
        Goal(user_id="local-user", title="Run a 5K", status=GoalStatus.ACTIVE.value))
    PostgresSafetyLog(factory).record(CrisisSignal(user_id="local-user", tier=CrisisTier.TIER_3.value))

    body = client.get("/memory/audit/full").json()
    assert body["total_memory_count"] == 1
    assert body["episodic"][0]["importance_label"] == "High"
    assert body["semantic"][0]["fact_text"] == "values independence"
    assert body["identity"][0]["fact_text"] == "Nova values honesty"
    assert body["crisis_session_count"] == 1
    assert body["active_goal_count"] == 1


def test_audit_query_matches_by_topic_tag():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="talked about hiking",
                         topic_tags=["hiking"])
    store.save_episodic(mem)

    body = client.get("/memory/audit/query?q=tell me about hiking").json()
    assert body["total_count"] == 1
    assert str(mem.memory_id) in body["memory_ids"]


def test_correct_memory_edit_updates_summary():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="wrong text")
    store.save_episodic(mem)

    resp = client.post(f"/memory/{mem.memory_id}/correct",
                       json={"correction_type": "edit", "new_content": "right text"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert store.get_episodic(mem.memory_id).summary == "right text"


def test_correct_memory_anchor_freezes_decay_and_marks_anchored():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="a keeper", decay_rate=0.02)
    store.save_episodic(mem)

    resp = client.post(f"/memory/{mem.memory_id}/correct", json={"correction_type": "anchor"})
    assert resp.status_code == 200
    got = store.get_episodic(mem.memory_id)
    assert got.is_anchored is True
    assert got.decay_rate == 0.0
    assert got.importance_score >= 0.95


def test_correct_memory_unknown_type_fails_without_mutating():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="unchanged")
    store.save_episodic(mem)

    resp = client.post(f"/memory/{mem.memory_id}/correct", json={"correction_type": "bogus"})
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert store.get_episodic(mem.memory_id).summary == "unchanged"


def test_integrity_reports_intact_chains():
    client, _ = _client()
    body = client.get("/memory/integrity").json()
    assert body["status"] == "INTACT"
    assert body["audit_chain_ok"] is True and body["privacy_chain_ok"] is True
    assert body["safety_chain_ok"] is True
