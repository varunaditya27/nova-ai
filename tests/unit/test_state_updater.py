"""Tests for the State Updater write path (architecture doc §12)."""

from datetime import datetime
from uuid import uuid4

from backend.layer2_memory.state_updater import state_updater
from backend.layer2_memory.audit_trail import AuditTrail
from backend.layer2_memory.memory_store import InMemoryMemoryStore
from backend.layer2_memory.schemas import (
    AuditEventType,
    EmotionVector,
    EpisodicMemory,
    ScoredMemory,
    ShortTermMemoryBuffer,
    UserWorldModel,
)

NOW = datetime(2026, 6, 26)


def _stm(user, session):
    return ShortTermMemoryBuffer(session_id=session, user_id=user)


def test_extracted_episodes_are_saved_and_audited():
    user, session = uuid4(), uuid4()
    store = InMemoryMemoryStore()
    audit = AuditTrail()

    def extractor(stm, emotion):
        return [EpisodicMemory(user_id=user, summary="had a hard day", S_current=0.8)]

    result = state_updater(
        user_id=user, session_id=session, stm_buffer=_stm(user, session),
        store=store, audit=audit, emotion=EmotionVector(), now=NOW, extractor_fn=extractor,
    )
    assert result.episodes_created == 1
    assert len(store.active_episodic(user)) == 1
    assert any(e.event_type == AuditEventType.MEMORY_CREATED for e in audit.events)
    assert audit.verify() is True


def test_reinforced_recall_increases_strength_and_audits():
    user, session = uuid4(), uuid4()
    store = InMemoryMemoryStore()
    audit = AuditTrail()
    mem = EpisodicMemory(user_id=user, summary="interview", S_current=0.5, reinforcement_count=0)
    store.save_episodic(mem)
    used = ScoredMemory(memory=mem, effective_score=0.8)
    used_flag = used
    used_flag.memory  # noqa - keep reference

    result = state_updater(
        user_id=user, session_id=session, stm_buffer=_stm(user, session),
        store=store, audit=audit, emotion=EmotionVector(), now=NOW,
        extractor_fn=lambda s, e: [], last_recall=[used], used_memory_ids={mem.memory_id},
    )
    assert mem.S_current > 0.5
    assert mem.reinforcement_count == 1
    assert result.memories_reinforced == 1
    assert any(e.event_type == AuditEventType.MEMORY_REINFORCED for e in audit.events)


def test_unused_recall_is_not_reinforced():
    user, session = uuid4(), uuid4()
    store = InMemoryMemoryStore()
    mem = EpisodicMemory(user_id=user, S_current=0.5)
    store.save_episodic(mem)
    result = state_updater(
        user_id=user, session_id=session, stm_buffer=_stm(user, session),
        store=store, audit=AuditTrail(), emotion=EmotionVector(), now=NOW,
        extractor_fn=lambda s, e: [], last_recall=[ScoredMemory(memory=mem)],
        used_memory_ids=set(),
    )
    assert mem.S_current == 0.5
    assert result.memories_reinforced == 0


def test_uwm_version_bumped_and_audited():
    user, session = uuid4(), uuid4()
    store = InMemoryMemoryStore()
    audit = AuditTrail()
    store.save_uwm(UserWorldModel(user_id=user, update_version=2))
    state_updater(
        user_id=user, session_id=session, stm_buffer=_stm(user, session),
        store=store, audit=audit, emotion=EmotionVector(), now=NOW,
        extractor_fn=lambda s, e: [],
    )
    assert store.load_uwm(user).update_version == 3
    assert any(e.event_type == AuditEventType.UWM_UPDATED for e in audit.events)


def test_audit_write_failure_does_not_block(monkeypatch):
    user, session = uuid4(), uuid4()
    store = InMemoryMemoryStore()

    class ExplodingAudit(AuditTrail):
        def append(self, event):
            raise RuntimeError("audit.db locked")

    # §15: audit write failure must not block the conversation/state update.
    result = state_updater(
        user_id=user, session_id=session, stm_buffer=_stm(user, session),
        store=store, audit=ExplodingAudit(), emotion=EmotionVector(), now=NOW,
        extractor_fn=lambda s, e: [EpisodicMemory(user_id=user, summary="x")],
    )
    assert result.episodes_created == 1
    assert len(store.active_episodic(user)) == 1
