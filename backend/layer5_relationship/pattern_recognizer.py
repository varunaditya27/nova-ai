"""SC-3 — Social Pattern Recognizer (architecture doc §5).

The analytical layer: looks across the accumulated event history and social graph to
identify recurring dynamics at three scopes — intra-relationship, cross-relationship
(user behavior), and temporal. Patterns are what separate genuine social intelligence
from simple event logging (§1, §13 principle 1).

Runs as a background batch process every 5 sessions, not per-message — real patterns
require longitudinal evidence and per-message detection would produce constant false
positives (§5.4). Deterministic; the topic-clustering step accepts an injected
``similarity_fn`` (token-overlap default) so it runs offline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer5_relationship.pattern_math import (
    cluster_by_semantic_similarity,
    compute_mention_counts_by_window,
    is_declining_trend,
    span_days as _span_days,
)
from backend.layer5_relationship.schemas import (
    PatternScope,
    SocialEvent,
    SocialEventType,
    SocialGraph,
    SocialPattern,
    SocialPatternType,
)

_CONFLICT_TYPES = {
    SocialEventType.CONFLICT_ONSET.value,
    SocialEventType.CONFLICT_ESCALATION.value,
}
_PATTERN_CONFIDENCE_FLOOR = 0.55
_CLUSTER_THRESHOLD = 0.72


def detect_patterns(
    social_graph: SocialGraph,
    event_history: list[SocialEvent],
    min_events: int = 3,
    min_span_days: int = 30,
    now: Optional[datetime] = None,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> list[SocialPattern]:
    """Detect all currently active social patterns (architecture doc §5.4).

    Returns patterns with confidence >= 0.55. Runs over the full event history (the
    every-5-sessions batch job), not a single message.
    """
    now = now or datetime.utcnow()
    patterns: list[SocialPattern] = []

    # ── Intra-relationship patterns ──────────────────────────────────────────
    for person_id, node in social_graph.nodes.items():
        person_events = sorted(
            [e for e in event_history if e.person_id == person_id and e.reported_timestamp],
            key=lambda e: e.reported_timestamp,
        )
        name = node.display_name or "this person"

        # Recurring conflict topic.
        conflict_events = [e for e in person_events if e.event_type in _CONFLICT_TYPES]
        if len(conflict_events) >= min_events:
            clusters = cluster_by_semantic_similarity(
                [e.summary for e in conflict_events], _CLUSTER_THRESHOLD, similarity_fn
            )
            for indices in clusters:
                cluster = [conflict_events[i] for i in indices]
                if len(cluster) >= 2 and _span_days(cluster) >= min_span_days:
                    span = _span_days(cluster)
                    patterns.append(SocialPattern(
                        pattern_type=SocialPatternType.RECURRING_CONFLICT_TOPIC.value,
                        scope=PatternScope.INTRA_RELATIONSHIP.value,
                        person_ids_involved=[person_id],
                        supporting_event_ids=[e.event_id for e in cluster],
                        event_count=len(cluster),
                        first_observed=cluster[0].reported_timestamp,
                        last_observed=cluster[-1].reported_timestamp,
                        observation_span_days=span,
                        pattern_confidence=min(0.95, 0.5 + len(cluster) * 0.1),
                        pattern_strength=min(1.0, len(cluster) / 10.0),
                        last_activation=cluster[-1].reported_timestamp,
                        plain_language_description=(
                            f"You've described conflict with {name} on a similar theme "
                            f"{len(cluster)} times over about {span} days."
                        ),
                        coaching_hook=f"a recurring conflict theme with {name}",
                    ))

        # Recurring support failure.
        support_failures = [e for e in person_events
                            if e.event_type == SocialEventType.SUPPORT_WITHHELD.value]
        if len(support_failures) >= 2 and _span_days(support_failures) >= min_span_days:
            patterns.append(SocialPattern(
                pattern_type=SocialPatternType.RECURRING_SUPPORT_FAILURE.value,
                scope=PatternScope.INTRA_RELATIONSHIP.value,
                person_ids_involved=[person_id],
                supporting_event_ids=[e.event_id for e in support_failures],
                event_count=len(support_failures),
                first_observed=support_failures[0].reported_timestamp,
                last_observed=support_failures[-1].reported_timestamp,
                observation_span_days=_span_days(support_failures),
                pattern_confidence=min(0.90, 0.5 + len(support_failures) * 0.1),
                pattern_strength=min(1.0, len(support_failures) / 8.0),
                last_activation=support_failures[-1].reported_timestamp,
                plain_language_description=(
                    f"From what you've shared, {name} hasn't been there for you "
                    f"{len(support_failures)} times."
                ),
                coaching_hook=f"support you expected from {name} that didn't come",
            ))

    # ── Cross-relationship patterns ──────────────────────────────────────────
    avoidance = [e for e in event_history
                 if e.event_type == SocialEventType.USER_AVOIDED_CONFLICT.value]
    unique_persons = {e.person_id for e in avoidance}
    if len(avoidance) >= 3 and len(unique_persons) >= 2:
        patterns.append(SocialPattern(
            pattern_type=SocialPatternType.CONFLICT_AVOIDANCE_PATTERN.value,
            scope=PatternScope.CROSS_RELATIONSHIP.value,
            person_ids_involved=list(unique_persons),
            supporting_event_ids=[e.event_id for e in avoidance],
            event_count=len(avoidance),
            pattern_confidence=min(0.90, 0.4 + len(avoidance) * 0.1),
            pattern_strength=min(1.0, len(avoidance) / 8.0),
            last_activation=now,
            plain_language_description=(
                f"You've described stepping back from conflict across "
                f"{len(unique_persons)} different relationships."
            ),
            coaching_hook="a tendency to step around conflict rather than into it",
        ))

    # ── Temporal patterns ────────────────────────────────────────────────────
    counts = compute_mention_counts_by_window(event_history, window_days=30, now=now)
    if is_declining_trend(counts, min_windows=3):
        patterns.append(SocialPattern(
            pattern_type=SocialPatternType.SOCIAL_WITHDRAWAL_PATTERN.value,
            scope=PatternScope.TEMPORAL.value,
            person_ids_involved=[],
            supporting_event_ids=[e.event_id for e in event_history],
            event_count=sum(counts),
            observation_span_days=len(counts) * 30,
            pattern_confidence=0.6,
            pattern_strength=min(1.0, (counts[0] - counts[-1]) / max(1, counts[0])),
            last_activation=now,
            plain_language_description=(
                "Your mentions of the people in your life have been tapering off "
                "over recent weeks."
            ),
            coaching_hook="a quiet pulling-back from social contact lately",
        ))

    return [p for p in patterns if p.pattern_confidence >= _PATTERN_CONFIDENCE_FLOOR]
