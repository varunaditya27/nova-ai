"""Tests for SC-7 Forgetting & Consolidation Engine (architecture doc §9)."""

from datetime import datetime, timedelta
from uuid import uuid4

from backend.layer2_memory import forgetting_engine as fce
from backend.layer2_memory.embedding import DeterministicEmbedder
from backend.layer2_memory.schemas import EpisodicMemory

NOW = datetime(2026, 6, 26)
EMB = DeterministicEmbedder(dim=64)


def _ep(text="exam anxiety", **kw):
    base = dict(user_id=uuid4(), summary=text, embedding=EMB.embed(text),
                created_at=NOW, last_decay_computed_at=NOW)
    base.update(kw)
    return EpisodicMemory(**base)


# ── Trigger conditions (§9.2) ────────────────────────────────────────────────
def test_should_trigger_fce_by_episode_count():
    assert fce.should_trigger_fce(new_episodes=50, sessions_since=0, days_since=0) is True


def test_should_trigger_fce_by_sessions():
    assert fce.should_trigger_fce(new_episodes=0, sessions_since=25, days_since=0) is True


def test_should_trigger_fce_by_calendar():
    assert fce.should_trigger_fce(new_episodes=0, sessions_since=0, days_since=14) is True


def test_should_not_trigger_below_all_thresholds():
    assert fce.should_trigger_fce(new_episodes=10, sessions_since=3, days_since=2) is False


# ── Decay sweep (§9.3) ───────────────────────────────────────────────────────
def test_decay_sweep_deletes_weak_unimportant():
    ep = _ep(S_current=0.5, decay_rate=0.1, importance_score=0.3,
             last_decay_computed_at=NOW - timedelta(days=100))
    deleted, archived = fce.decay_sweep([ep], now=NOW)
    assert ep.is_deleted is True
    assert deleted == 1 and archived == 0


def test_decay_sweep_archives_weak_important():
    ep = _ep(S_current=0.5, decay_rate=0.1, importance_score=0.7,
             last_decay_computed_at=NOW - timedelta(days=100))
    deleted, archived = fce.decay_sweep([ep], now=NOW)
    assert ep.is_archived is True
    assert deleted == 0 and archived == 1


def test_decay_sweep_keeps_strong_memory():
    ep = _ep(S_current=0.9, decay_rate=0.01, importance_score=0.8,
             last_decay_computed_at=NOW - timedelta(days=1))
    fce.decay_sweep([ep], now=NOW)
    assert ep.is_deleted is False and ep.is_archived is False


# ── Cluster detection (§9.4) ─────────────────────────────────────────────────
def test_cluster_detection_groups_similar_and_requires_three():
    a, b, c = _ep("exam anxiety"), _ep("exam anxiety"), _ep("exam anxiety")
    odd = _ep("favorite pizza topping")
    clusters = fce.cluster_detection([a, b, c, odd], threshold=0.85, min_members=3)
    assert len(clusters) == 1
    assert set(id(m) for m in clusters[0].members) == {id(a), id(b), id(c)}


def test_cluster_detection_ignores_small_groups():
    a, b = _ep("exam anxiety"), _ep("exam anxiety")
    clusters = fce.cluster_detection([a, b], threshold=0.85, min_members=3)
    assert clusters == []


# ── Semantic extraction (§9.5) ───────────────────────────────────────────────
def test_extract_semantic_marks_members_consolidated():
    user = uuid4()
    members = [_ep("exam anxiety", user_id=user) for _ in range(3)]
    from backend.layer2_memory.schemas import EpisodicCluster
    cluster = EpisodicCluster(members=members)
    semantic = fce.extract_semantic_memory(
        cluster, user_id=user, generalize_fn=lambda summaries: "User experiences exam anxiety",
        now=NOW,
    )
    assert semantic.statement == "User experiences exam anxiety"
    assert semantic.evidence_count == 3
    assert semantic.confidence == 0.65  # 0.5 + 0.05*3
    for m in members:
        assert m.is_deleted is True
        assert m.consolidated_into == semantic.memory_id
