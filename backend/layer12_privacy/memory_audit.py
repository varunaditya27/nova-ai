"""SC-3 — Memory Audit: the transparency interface (architecture doc §5).

A complete, human-readable, queryable view of everything Nova knows about the user — the most
trust-building surface in the product. Without it, privacy is a claim; with it, it is verifiable.
This module builds the audit view, classifies natural-language audit queries by intent, runs them
against the (duck-typed) stores, and produces provenance records. Deterministic; no embeddings or
raw scores are exposed — only human-readable labels.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer12_privacy.schemas import (
    AuditableFact,
    AuditableMemory,
    AuditQueryResult,
    MemoryAuditView,
    ProvenanceRecord,
)

_TEMPORAL_MARKERS = ("last year", "last month", "last week", "from ", "ago", "recently",
                     "over the past", "this year")
_IDENTITY_MARKERS = ("value", "values", "believe", "belief", "who i am", "my identity")
_PATTERN_MARKERS = ("pattern", "patterns", "habit", "habits", "tend to", "always")


def map_importance_to_label(score: float, anchored: bool = False) -> str:
    """Map a raw importance score to a human-readable label (architecture doc §5.2)."""
    if anchored:
        return "Anchored"
    if score >= 0.70:
        return "High"
    if score >= 0.40:
        return "Medium"
    return "Low"


def _to_auditable_memory(m) -> AuditableMemory:
    return AuditableMemory(
        memory_id=m.memory_id, date_formed=getattr(m, "created_at", None),
        human_readable_summary=getattr(m, "human_readable_summary", "")
        or getattr(m, "summary", ""),
        importance_label=map_importance_to_label(getattr(m, "importance_score", 0.0),
                                                 getattr(m, "is_anchored", False)),
        topic_tags=list(getattr(m, "topic_tags", []) or []),
        emotion_at_formation=getattr(m, "emotion_at_formation", "neutral"),
        reinforcement_count=getattr(m, "reinforcement_count", 0))


def _to_auditable_fact(f) -> AuditableFact:
    """Layer 2's real SemanticMemory has memory_id/statement/supporting_episode_ids/memory_type —
    not fact_id/fact_text/source_episode_ids/category, which would raise AttributeError the first
    time a real semantic_store was ever passed in (same class of bug already found and fixed in
    dry_run_deletion's cascade check, docs/POLISH_BACKLOG.md)."""
    return AuditableFact(
        fact_id=str(f.memory_id), fact_text=getattr(f, "statement", ""),
        category=getattr(getattr(f, "memory_type", ""), "value", getattr(f, "memory_type", "")),
        confidence=getattr(f, "confidence", 0.0),
        source_episode_ids=[str(e) for e in getattr(f, "supporting_episode_ids", []) or []],
        is_user_confirmed=getattr(f, "S_current", 1.0) >= 1.0 and not getattr(f, "is_deprecated", False))


def _to_auditable_identity(b) -> AuditableFact:
    """Layer 2's real IdentityMemory has belief_id/statement/category(IdentityCategory)/
    is_immutable — distinct fields from SemanticMemory, so it needs its own converter rather than
    forcing one function to duck-type both real schemas."""
    return AuditableFact(
        fact_id=str(b.belief_id), fact_text=getattr(b, "statement", ""),
        category=getattr(getattr(b, "category", ""), "value", getattr(b, "category", "")),
        confidence=getattr(b, "centrality", 0.0), source_episode_ids=[],
        is_user_confirmed=getattr(b, "is_immutable", False))


def generate_audit_view(
    user_id: str, memory_store, semantic_store=None, identity_store=None,
    safety_store=None, goal_store=None, now: Optional[datetime] = None,
) -> MemoryAuditView:
    """Assemble the full, human-readable Memory Audit view (architecture doc §5.2)."""
    episodic = [_to_auditable_memory(m) for m in memory_store.all()]
    semantic = [_to_auditable_fact(f) for f in (semantic_store.all() if semantic_store else [])]
    identity = [_to_auditable_identity(b) for b in (identity_store.all() if identity_store else [])]

    crisis_count = 0
    if safety_store is not None:
        getter = getattr(safety_store, "crisis_session_count", None)
        crisis_count = getter() if callable(getter) else (getter or 0)

    active_goals = 0
    if goal_store is not None:
        getter = getattr(goal_store, "active_goal_count", None)
        active_goals = getter() if callable(getter) else (getter or 0)

    return MemoryAuditView(
        user_id=user_id, generated_at=now or datetime.utcnow(),
        total_memory_count=len(episodic), episodic=episodic, semantic=semantic,
        identity=identity, crisis_session_count=crisis_count, active_goal_count=active_goals)


def classify_query_intent(natural_language_query: str) -> str:
    """Classify an audit query into one of the intent types (architecture doc §5.3)."""
    low = (natural_language_query or "").lower()
    if any(m in low for m in _TEMPORAL_MARKERS):
        return "temporal_query"
    if any(m in low for m in _IDENTITY_MARKERS):
        return "identity_query"
    if any(m in low for m in _PATTERN_MARKERS):
        return "pattern_query"
    return "topic_query"


def _extract_topics(text: str) -> list:
    stop = {"what", "do", "you", "know", "about", "my", "tell", "me", "the", "a", "an", "is",
            "are", "have", "remember", "from", "of", "your"}
    return [w.strip("?.,") for w in (text or "").lower().split() if w.strip("?.,") not in stop and w]


def query(
    natural_language_query: str, memory_store, semantic_store=None, identity_store=None,
) -> AuditQueryResult:
    """Run a natural-language audit query against the live stores (architecture doc §5.3)."""
    intent = classify_query_intent(natural_language_query)
    topics = set(_extract_topics(natural_language_query))
    records = []
    for m in memory_store.all():
        if topics & set(getattr(m, "topic_tags", []) or []):
            records.append(m)
    if intent == "identity_query" and identity_store is not None:
        records += identity_store.all()
    return AuditQueryResult(query=natural_language_query, records=records,
                            total_count=len(records), intent_type=intent)


def build_provenance(memory, primary_session_id: Optional[str] = None) -> ProvenanceRecord:
    """Build the provenance record for a memory (architecture doc §5.4)."""
    return ProvenanceRecord(
        memory_id=memory.memory_id, memory_type=getattr(memory, "memory_type", "episodic"),
        primary_session_id=primary_session_id, first_formed=getattr(memory, "created_at", None),
        total_reinforcement_count=getattr(memory, "reinforcement_count", 0),
        contributed_to_semantic_facts=list(getattr(memory, "derived_semantic_facts", []) or []))
