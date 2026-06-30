"""Integration: Layer 2 memory consolidation over the real Forgetting & Consolidation Engine.

Drives the actual FCE primitives end-to-end (trigger → decay sweep → cluster detection →
semantic extraction) to prove the storage/processing sub-components interoperate: weak memories
decay out, an important one is archived (not deleted), a repeated cluster is detected, and the
cluster compresses into a single semantic memory whose members are consolidated.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from backend.layer2_memory.forgetting_engine import (
    cluster_detection,
    decay_sweep,
    extract_semantic_memory,
    should_trigger_fce,
)
from backend.layer2_memory.schemas import EpisodicMemory

NOW = datetime(2025, 6, 1)
USER = uuid4()


def _ep(summary, emb, *, importance, s_current, created_days_ago, tags=None):
    return EpisodicMemory(
        user_id=USER, summary=summary, embedding=emb, topic_tags=tags or [],
        created_at=NOW - timedelta(days=created_days_ago),
        last_decay_computed_at=NOW - timedelta(days=created_days_ago),
        importance_score=importance, S_current=s_current, decay_rate=0.10)


def test_fce_triggers_on_episode_volume():
    assert should_trigger_fce(new_episodes=60, sessions_since=0, days_since=0) is True
    assert should_trigger_fce(new_episodes=1, sessions_since=1, days_since=1) is False


def test_decay_sweep_deletes_weak_keeps_strong_archives_important():
    weak = _ep("trivial chatter", [1.0, 0.0], importance=0.1, s_current=0.2, created_days_ago=60)
    important = _ep("told me their father passed away", [0.0, 1.0],
                    importance=0.9, s_current=0.2, created_days_ago=60)
    strong = _ep("ongoing project they care about", [0.5, 0.5],
                 importance=0.8, s_current=5.0, created_days_ago=1)
    deleted, archived = decay_sweep([weak, important, strong], NOW)
    assert weak.is_deleted is True                 # weak + unimportant → deleted
    assert important.is_archived is True           # weak + important → archived, retained
    assert strong.is_deleted is False and strong.is_archived is False
    assert deleted == 1 and archived == 1


def test_cluster_detection_then_semantic_extraction():
    # three near-identical "Sunday anxiety" episodes form one cluster
    eps = [_ep(f"anxious again on Sunday evening #{i}", [1.0, 0.0, 0.0],
               importance=0.6, s_current=3.0, created_days_ago=i, tags=["mood"]) for i in range(3)]
    noise = _ep("watched a film", [0.0, 0.0, 1.0], importance=0.3, s_current=3.0, created_days_ago=2)
    clusters = cluster_detection(eps + [noise], threshold=0.9, min_members=3)
    assert len(clusters) == 1 and len(clusters[0].members) == 3

    semantic = extract_semantic_memory(
        clusters[0], USER, generalize_fn=lambda summaries: "Tends to feel anxious on Sundays", now=NOW)
    assert semantic.statement == "Tends to feel anxious on Sundays"
    assert semantic.evidence_count == 3
    # members are consolidated into the new semantic memory (non-destructive lineage)
    assert all(e.consolidated_into == semantic.memory_id and e.is_deleted for e in clusters[0].members)
