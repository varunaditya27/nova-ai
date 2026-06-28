"""Tests for SC-3 Social Pattern Recognizer (architecture doc §5)."""

from datetime import datetime, timedelta

from backend.layer5_relationship import pattern_recognizer as pr
from backend.layer5_relationship.schemas import (
    PatternScope,
    SocialEvent,
    SocialEventType,
    SocialGraph,
    SocialNode,
    SocialPatternType,
)

NOW = datetime(2026, 6, 28)


def _event(person_id, event_type, days_ago, summary=""):
    return SocialEvent(person_id=person_id, event_type=event_type,
                       summary=summary, reported_timestamp=NOW - timedelta(days=days_ago),
                       emotional_intensity=0.6)


def _graph(*nodes):
    return SocialGraph(nodes={n.person_id: n for n in nodes})


# ── Clustering helper (§5.4) ─────────────────────────────────────────────────
def test_cluster_groups_similar_summaries():
    summaries = ["conflict about shared space", "fight over shared space",
                 "argument over the dishes again"]
    clusters = pr.cluster_by_semantic_similarity(summaries, threshold=0.4)
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2]      # two "shared space" cluster together, dishes alone


def test_cluster_uses_injected_similarity_fn():
    clusters = pr.cluster_by_semantic_similarity(
        ["a", "b", "c"], threshold=0.5, similarity_fn=lambda x, y: 0.9)
    assert len(clusters) == 1   # everything similar → one cluster


# ── Temporal-trend helpers (§5.4) ────────────────────────────────────────────
def test_mention_counts_by_window():
    events = [_event("p1", SocialEventType.CONFLICT_ONSET.value, d) for d in (5, 35, 65)]
    counts = pr.compute_mention_counts_by_window(events, window_days=30, now=NOW)
    assert len(counts) >= 3
    assert sum(counts) == 3


def test_is_declining_trend():
    assert pr.is_declining_trend([5, 3, 1], min_windows=3) is True
    assert pr.is_declining_trend([1, 3, 5], min_windows=3) is False
    assert pr.is_declining_trend([5, 3], min_windows=3) is False   # too few windows


# ── Intra-relationship patterns (§5.4) ───────────────────────────────────────
def test_detect_recurring_conflict_topic():
    node = SocialNode(person_id="p1", display_name="Riya")
    events = [_event("p1", SocialEventType.CONFLICT_ONSET.value, d, "conflict about shared space")
              for d in (120, 70, 20)]
    patterns = pr.detect_patterns(_graph(node), events, now=NOW)
    types = [p.pattern_type for p in patterns]
    assert SocialPatternType.RECURRING_CONFLICT_TOPIC.value in types
    p = next(p for p in patterns if p.pattern_type == SocialPatternType.RECURRING_CONFLICT_TOPIC.value)
    assert p.person_ids_involved == ["p1"]
    assert p.pattern_confidence >= 0.55
    assert p.plain_language_description
    assert p.coaching_hook


def test_detect_recurring_support_failure():
    node = SocialNode(person_id="p1", display_name="Mom")
    events = [_event("p1", SocialEventType.SUPPORT_WITHHELD.value, d) for d in (90, 20)]
    patterns = pr.detect_patterns(_graph(node), events, now=NOW)
    assert SocialPatternType.RECURRING_SUPPORT_FAILURE.value in [p.pattern_type for p in patterns]


# ── Cross-relationship pattern (§5.4) ────────────────────────────────────────
def test_detect_conflict_avoidance_cross_relationship():
    n1, n2 = SocialNode(person_id="p1"), SocialNode(person_id="p2")
    events = [
        _event("p1", SocialEventType.USER_AVOIDED_CONFLICT.value, 60),
        _event("p2", SocialEventType.USER_AVOIDED_CONFLICT.value, 30),
        _event("p1", SocialEventType.USER_AVOIDED_CONFLICT.value, 10),
    ]
    patterns = pr.detect_patterns(_graph(n1, n2), events, now=NOW)
    p = next((p for p in patterns
              if p.pattern_type == SocialPatternType.CONFLICT_AVOIDANCE_PATTERN.value), None)
    assert p is not None
    assert p.scope == PatternScope.CROSS_RELATIONSHIP.value
    assert set(p.person_ids_involved) == {"p1", "p2"}


# ── Temporal pattern (§5.4) ──────────────────────────────────────────────────
def test_detect_social_withdrawal_temporal():
    # Declining mentions across windows: many old, few recent.
    events = (
        [_event("p1", SocialEventType.CONFLICT_ONSET.value, d) for d in (75, 72, 70, 68)] +
        [_event("p1", SocialEventType.CONFLICT_ONSET.value, d) for d in (45, 42)] +
        [_event("p1", SocialEventType.CONFLICT_ONSET.value, 10)]
    )
    patterns = pr.detect_patterns(_graph(SocialNode(person_id="p1")), events, now=NOW)
    assert SocialPatternType.SOCIAL_WITHDRAWAL_PATTERN.value in [p.pattern_type for p in patterns]
    p = next(p for p in patterns
             if p.pattern_type == SocialPatternType.SOCIAL_WITHDRAWAL_PATTERN.value)
    assert p.scope == PatternScope.TEMPORAL.value
    assert p.person_ids_involved == []


# ── Insufficient evidence (§5.4) ─────────────────────────────────────────────
def test_no_patterns_when_insufficient_evidence():
    node = SocialNode(person_id="p1", display_name="Sam")
    events = [_event("p1", SocialEventType.CONFLICT_ONSET.value, 5, "minor thing")]
    assert pr.detect_patterns(_graph(node), events, now=NOW) == []
