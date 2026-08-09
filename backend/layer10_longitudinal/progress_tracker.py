"""SC-3 — Progress & Pattern Tracker (architecture doc §5).

Holds the longitudinal *numbers* behind the narrative: rolling emotional metrics, goal
achievement rates, life-domain balance, and detected behavioral patterns. Deterministic; keyed
off an injected ``as_of_date`` so windows are reproducible. Pattern detection requires both a
minimum occurrence count and a confidence floor so signal is separated from noise (§5.3).
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from backend.layer10_longitudinal.schemas import (
    BehavioralPattern,
    LifeDomainBalance,
    PatternType,
    ProgressSnapshot,
)

TRACKED_DOMAINS = ["career", "health", "relationships", "learning",
                   "creativity", "finance", "personal_growth"]
_NEGLECTED_FLOOR = 0.08
_TREND_DELTA = 0.10


# ── Pattern detection (§5.3) ─────────────────────────────────────────────────
def detect_behavioral_patterns(
    emotional_records: list,
    session_records: list,
    episodic_records: list,
    min_occurrences: int = 3,
    min_confidence: float = 0.65,
) -> list[BehavioralPattern]:
    """Detect recurring patterns from longitudinal data (architecture doc §5.3)."""
    patterns: list[BehavioralPattern] = []

    # Pattern 1 — emotional cycle by day-of-week.
    if emotional_records:
        overall_mean = sum(r.valence for r in emotional_records) / len(emotional_records)
        dow_recs: dict[str, list] = defaultdict(list)
        for r in emotional_records:
            dow_recs[r.date.strftime("%A")].append(r)
        for day, recs in dow_recs.items():
            if len(recs) < min_occurrences:
                continue
            mean_v = sum(r.valence for r in recs) / len(recs)
            if mean_v < overall_mean - 0.20:
                confidence = min(1.0, len(recs) / 12)
                if confidence >= min_confidence:
                    patterns.append(BehavioralPattern(
                        description=f"Emotional dip on {day}s "
                                    f"(avg valence {mean_v:.2f} vs overall {overall_mean:.2f})",
                        pattern_type=PatternType.EMOTIONAL_CYCLE.value,
                        first_detected_date=min(r.date for r in recs),
                        last_observed_date=max(r.date for r in recs),
                        confidence=confidence, occurrence_count=len(recs)))

    # Pattern 2 — topic recurrence over 4+ weeks.
    topic_dates: dict[str, list] = defaultdict(list)
    for e in episodic_records:
        for t in e.topics:
            topic_dates[t].append(e.date)
    for topic, dates in topic_dates.items():
        if len(dates) < min_occurrences:
            continue
        week_span = (max(dates) - min(dates)).days / 7
        if week_span < 4:
            continue
        confidence = min(1.0, len(dates) / 10)
        if confidence >= min_confidence:
            patterns.append(BehavioralPattern(
                description=f'Recurring topic: "{topic}" — {len(dates)} sessions '
                            f"over {week_span:.0f} weeks",
                pattern_type=PatternType.TOPIC_RECURRENCE.value,
                first_detected_date=min(dates), last_observed_date=max(dates),
                confidence=confidence, occurrence_count=len(dates)))

    return patterns


# ── Domain balance (§5.2) ────────────────────────────────────────────────────
def compute_domain_balance(episodic_records: list) -> LifeDomainBalance:
    """Entropy-based distribution of topics across life domains (architecture doc §5.2)."""
    counts: dict[str, int] = defaultdict(int)
    total = 0
    for e in episodic_records:
        for t in e.topics:
            counts[t] += 1
            total += 1
    if total == 0:
        return LifeDomainBalance()

    weights = {d: c / total for d, c in counts.items()}
    dominant = max(weights, key=weights.get)
    neglected = sorted(d for d, w in weights.items() if w < _NEGLECTED_FLOOR)

    # Normalized Shannon entropy as balance score (1.0 = perfectly even).
    entropy = -sum(w * math.log(w) for w in weights.values() if w > 0)
    max_entropy = math.log(len(weights)) if len(weights) > 1 else 1.0
    balance_score = (entropy / max_entropy) if max_entropy > 0 else 0.0

    return LifeDomainBalance(domain_weights=weights, dominant_domain=dominant,
                             neglected_domains=neglected, balance_score=round(balance_score, 4))


# ── Progress snapshot (§5.2) ─────────────────────────────────────────────────
def _avg_valence(records: list, as_of: date, window_days: int) -> float:
    cutoff = as_of - timedelta(days=window_days)
    window = [r.valence for r in records if cutoff <= r.date <= as_of]
    return sum(window) / len(window) if window else 0.0


def compute_progress_snapshot(
    user_id: str,
    as_of_date: date,
    emotional_records: list,
    sessions: list,
    goals: list,
    episodic_records: Optional[list] = None,
) -> ProgressSnapshot:
    """Compute a longitudinal progress snapshot (architecture doc §5.2)."""
    episodic_records = episodic_records or []

    # Layer 7's real GoalStatus terminal value is "completed", not "achieved" -- this mismatch
    # meant goals_achieved_lifetime/achievement_rate_lifetime silently stayed 0 for every real
    # user the moment this function was ever fed real Goal objects (see docs/POLISH_BACKLOG.md).
    achieved = sum(1 for g in goals if getattr(g, "status", "") == "completed")
    abandoned = sum(1 for g in goals if getattr(g, "status", "") == "abandoned")
    rate = achieved / (achieved + abandoned) if (achieved + abandoned) else 0.0

    avg_4w = _avg_valence(emotional_records, as_of_date, 28)
    avg_12w = _avg_valence(emotional_records, as_of_date, 84)
    recent = _avg_valence(emotional_records, as_of_date, 14)
    older_cut_hi = as_of_date - timedelta(days=14)
    older_cut_lo = as_of_date - timedelta(days=42)
    older_vals = [r.valence for r in emotional_records if older_cut_lo <= r.date < older_cut_hi]
    older = sum(older_vals) / len(older_vals) if older_vals else recent
    trend = ("improving" if recent > older + _TREND_DELTA
             else "declining" if recent < older - _TREND_DELTA else "stable")

    crisis_30d = sum(1 for s in sessions
                     if s.crisis_mode_active and s.date >= as_of_date - timedelta(days=30))
    sessions_4w = [s for s in sessions if s.date >= as_of_date - timedelta(days=28)]
    high_intensity = [r for r in emotional_records if r.emotional_intensity > 0.70]
    high_freq = len(high_intensity) / len(emotional_records) if emotional_records else 0.0

    # Resilience proxy: higher average valence + lower volatility → more resilient.
    vals = [r.valence for r in emotional_records]
    if vals:
        mean_v = sum(vals) / len(vals)
        spread = (max(vals) - min(vals)) / 2
        resilience = max(0.0, min(1.0, (mean_v + 1) / 2 * (1 - spread / 2)))
    else:
        resilience = 0.0

    return ProgressSnapshot(
        user_id=user_id, as_of_date=as_of_date, snapshot_version=1,
        avg_valence_4w=avg_4w, avg_valence_12w=avg_12w, valence_trend_short=trend,
        high_intensity_frequency=round(high_freq, 4), crisis_event_frequency=float(crisis_30d),
        resilience_score=round(resilience, 4),
        total_goals_lifetime=len(goals), goals_achieved_lifetime=achieved,
        goals_abandoned_lifetime=abandoned, achievement_rate_lifetime=rate,
        avg_sessions_per_week_4w=len(sessions_4w) / 4 if sessions_4w else 0.0,
        domain_balance=compute_domain_balance(episodic_records),
        active_patterns=detect_behavioral_patterns(emotional_records, sessions, episodic_records))
