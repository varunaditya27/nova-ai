"""SC-7 · Forgetting & Consolidation Engine (architecture doc §9).

How Nova learns without fine-tuning. Runs periodically (background job, never per-message)
and performs three operations: decay sweep → cluster detection → semantic extraction. Repeated
episodic patterns compress into stable semantic facts; irrelevant episodes are deleted.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional
from uuid import UUID

from . import memory_strength as ms
from . import semantic_memory as sm
from .embedding import cosine_similarity
from .schemas import EpisodicCluster, EpisodicMemory, SemanticMemory, SemanticMemoryType

# Trigger thresholds (§9.2).
EPISODE_COUNT_TRIGGER = 50
SESSION_COUNT_TRIGGER = 25
CALENDAR_DAYS_TRIGGER = 14

# Clustering parameters (§9.4).
CLUSTER_SIMILARITY_THRESHOLD = 0.85
CLUSTER_MIN_MEMBERS = 3

# A generalizer: cluster member summaries → one stable statement. Production wires an LLM;
# tests inject a deterministic function.
Generalizer = Callable[[list[str]], str]


def should_trigger_fce(new_episodes: int, sessions_since: int, days_since: int) -> bool:
    """Whether the FCE should run, given activity since the last run (§9.2)."""
    return (
        new_episodes >= EPISODE_COUNT_TRIGGER
        or sessions_since >= SESSION_COUNT_TRIGGER
        or days_since >= CALENDAR_DAYS_TRIGGER
    )


def decay_sweep(episodes: list[EpisodicMemory], now: datetime) -> tuple[int, int]:
    """Recompute strength and delete/archive weak memories (§9.3). Returns (deleted, archived)."""
    deleted = archived = 0
    today = now.date() if isinstance(now, datetime) else now
    for ep in episodes:
        if ep.is_deleted:
            continue
        # Layer-12 SC-3's EXPIRE correction (§5.5) sets this; honor it unconditionally, ahead of
        # (and regardless of) the strength-based decision below -- a user-requested expiry isn't
        # negotiable by importance or reinforcement the way natural decay is.
        if getattr(ep, "auto_expiry_date", None) is not None and today >= ep.auto_expiry_date:
            ep.is_deleted = True
            deleted += 1
            continue
        last = ep.last_decay_computed_at or ep.created_at or now
        time_elapsed_days = max(0.0, (now - last).total_seconds() / 86400.0)
        ep.S_current = ms.decayed_strength(ep.S_current, ep.decay_rate, time_elapsed_days)
        ep.last_decay_computed_at = now

        decision = ms.deletion_decision(ep.S_current, ep.importance_score)
        if decision == "delete":
            ep.is_deleted = True
            deleted += 1
        elif decision == "archive":
            ep.is_archived = True
            archived += 1
    return deleted, archived


def cluster_detection(
    episodes: list[EpisodicMemory],
    threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
    min_members: int = CLUSTER_MIN_MEMBERS,
) -> list[EpisodicCluster]:
    """Agglomerative complete-linkage clustering over embeddings (§9.4).

    Complete linkage (every pair in a cluster must exceed the similarity threshold) yields
    compact, well-separated clusters and prevents nearest-neighbor chaining. Deterministic.
    Only clusters with ≥ ``min_members`` are returned (a pattern requires repetition).
    """
    active = [e for e in episodes if not e.is_deleted and e.embedding]
    groups: list[list[int]] = [[i] for i in range(len(active))]

    def complete_linkage_sim(a: list[int], b: list[int]) -> float:
        return min(
            cosine_similarity(active[i].embedding, active[j].embedding) for i in a for j in b
        )

    while True:
        best_pair: Optional[tuple[int, int]] = None
        best_sim = threshold
        for x in range(len(groups)):
            for y in range(x + 1, len(groups)):
                sim = complete_linkage_sim(groups[x], groups[y])
                if sim >= best_sim:
                    best_sim = sim
                    best_pair = (x, y)
        if best_pair is None:
            break
        x, y = best_pair
        groups[x].extend(groups[y])
        del groups[y]

    clusters = [
        EpisodicCluster(members=[active[i] for i in g]) for g in groups if len(g) >= min_members
    ]
    return clusters


def extract_semantic_memory(
    cluster: EpisodicCluster,
    user_id: UUID,
    generalize_fn: Generalizer,
    now: datetime,
    memory_type: SemanticMemoryType = SemanticMemoryType.BEHAVIORAL_TENDENCY,
) -> SemanticMemory:
    """Compress a cluster into one stable semantic memory and consolidate its members (§9.5)."""
    summaries = [e.summary for e in cluster.members]
    statement = generalize_fn(summaries)
    most_recent = cluster.most_recent_episode

    semantic = SemanticMemory(
        user_id=user_id,
        memory_type=memory_type,
        statement=statement,
        confidence=sm.compute_initial_confidence(len(cluster.members)),
        supporting_episode_ids=[e.memory_id for e in cluster.members],
        evidence_count=len(cluster.members),
        created_at=now,
        last_confirmed_at=most_recent.created_at if most_recent else now,
        decay_rate=0.005,
    )

    for ep in cluster.members:
        ep.consolidated_into = semantic.memory_id
        ep.is_deleted = True
    return semantic
