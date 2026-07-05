import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer2_memory.schemas import AuditEvent, AuditEventType
from infra.db.engine import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.audit_trail import PostgresAuditTrail


def _factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def _event(reason):
    return AuditEvent(user_id="u1", timestamp=datetime.now(timezone.utc),
                      event_type=AuditEventType.MEMORY_CREATED, reason=reason,
                      triggered_by="test")


def test_append_builds_verifiable_chain():
    f = _factory()
    trail = PostgresAuditTrail(f, "u1")
    e1 = trail.append(_event("first"))
    e2 = trail.append(_event("second"))
    assert e1.content_hash and e2.prev_event_hash == e1.content_hash
    assert trail.verify() is True


def test_chain_continues_across_restart():
    f = _factory()
    PostgresAuditTrail(f, "u1").append(_event("first"))
    first_hash = PostgresAuditTrail(f, "u1")._head
    # A brand-new trail object over the same DB continues the chain.
    e2 = PostgresAuditTrail(f, "u1").append(_event("second"))
    assert e2.prev_event_hash == first_hash


def test_tampering_a_row_fails_verify():
    f = _factory()
    trail = PostgresAuditTrail(f, "u1")
    trail.append(_event("first"))
    trail.append(_event("second"))
    with session_scope(f) as s:
        row = s.query(models.MemoryAudit).order_by(models.MemoryAudit.id.asc()).first()
        payload = dict(row.payload)
        payload["reason"] = "tampered"
        row.payload = payload
    assert PostgresAuditTrail(f, "u1").verify() is False
