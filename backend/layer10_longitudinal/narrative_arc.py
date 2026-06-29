"""SC-1 — Narrative Arc construction (architecture doc §3.2-§3.4).

Detects chapter boundaries from life-event signals, computes the emotional arc of a period, and
assembles the chronological NarrativeArc. Deterministic — boundaries and arcs *emerge from the
data*, they are not user-marked. Interpretive narrative text is produced by the Life Narrative
Engine (an injected LLM); this module owns the structural/quantitative layer.
"""

from __future__ import annotations

from datetime import date
from statistics import pstdev
from typing import Optional

from backend.layer10_longitudinal.schemas import (
    EmotionalArcSummary,
    LifeChapter,
    LifeEvent,
    NarrativeArc,
)

# Life-event categories that always open a new chapter (architecture doc §3.4).
CHAPTER_BOUNDARY_CATEGORIES = {
    "career_transition", "educational_transition", "relational_major",
    "geographic_relocation", "major_loss", "health_major",
}
MIN_CHAPTER_DURATION_DAYS = 21


def detect_chapter_boundaries(
    life_events: list[LifeEvent], now: Optional[date] = None,
    min_chapter_duration_days: int = MIN_CHAPTER_DURATION_DAYS,
) -> list[date]:
    """Return ordered boundary dates from qualifying life events (architecture doc §3.4).

    A boundary within ``min_chapter_duration_days`` of the previous accepted boundary is dropped
    to prevent micro-chapters from event noise.
    """
    candidates = sorted(
        e.event_date for e in life_events if e.category in CHAPTER_BOUNDARY_CATEGORIES)
    boundaries: list[date] = []
    for d in candidates:
        if not boundaries or (d - boundaries[-1]).days >= min_chapter_duration_days:
            boundaries.append(d)
    return boundaries


def compute_emotional_arc(emotional_records: list) -> EmotionalArcSummary:
    """Summarize how emotional tone evolved across a period (architecture doc §3.2)."""
    if not emotional_records:
        return EmotionalArcSummary()
    recs = sorted(emotional_records, key=lambda r: r.date)
    valences = [r.valence for r in recs]
    opening, closing = valences[0], valences[-1]
    rng = max(valences) - min(valences)
    variance = pstdev(valences) if len(valences) > 1 else 0.0
    mean_v = sum(valences) / len(valences)

    # Dominant emotion = most frequent primary_emotion.
    counts: dict[str, int] = {}
    for r in recs:
        counts[r.primary_emotion] = counts.get(r.primary_emotion, 0) + 1
    dominant = max(counts, key=counts.get)

    trough = min(valences)
    trough_idx = valences.index(trough)
    delta = closing - opening

    if trough < opening - 0.20 and trough < closing - 0.20 and 0 < trough_idx < len(valences) - 1:
        trajectory = "recovering"
    elif variance > 0.45:
        trajectory = "volatile"
    elif delta > 0.15:
        trajectory = "improving"
    elif delta < -0.15:
        trajectory = "declining"
    elif mean_v > 0.2:
        trajectory = "stable_positive"
    elif mean_v < -0.2:
        trajectory = "stable_negative"
    else:
        trajectory = "mixed"

    peaks = [(r.date, r.valence) for r in recs if r.valence >= 0.6]
    troughs = [(r.date, r.valence) for r in recs if r.valence <= -0.6]
    return EmotionalArcSummary(
        opening_valence=opening, closing_valence=closing, dominant_emotion=dominant,
        emotional_range=rng, trajectory=trajectory, notable_peaks=peaks, notable_troughs=troughs)


def assign_chapter_title(life_events: list[LifeEvent], themes: Optional[list] = None) -> str:
    """Deterministically pick a chapter title from its anchoring event or theme (doc §3.3)."""
    if life_events:
        anchor = max(life_events, key=lambda e: e.significance_score)
        return anchor.title
    if themes:
        return themes[0]
    return "A new chapter"


def build_narrative_arc(
    user_id: str,
    arc_start_date: date,
    life_events: list[LifeEvent],
    emotional_records: list,
    now: Optional[date] = None,
) -> NarrativeArc:
    """Assemble the chronological arc, splitting chapters at detected boundaries (doc §3.2)."""
    now = now or date.today()
    boundaries = detect_chapter_boundaries(life_events, now=now)
    starts = [arc_start_date] + boundaries
    chapters: list[LifeChapter] = []

    for i, start in enumerate(starts):
        is_last = i == len(starts) - 1
        end = None if is_last else starts[i + 1]
        window_events = [e for e in life_events
                         if start <= e.event_date and (end is None or e.event_date < end)]
        window_emo = [r for r in emotional_records
                      if start <= r.date and (end is None or r.date < end)]
        chapters.append(LifeChapter(
            title=assign_chapter_title(window_events),
            start_date=start, end_date=end, is_current=is_last,
            emotional_arc=compute_emotional_arc(window_emo),
            life_events=[e.event_id for e in window_events]))

    return NarrativeArc(
        user_id=user_id, arc_start_date=arc_start_date, chapters=chapters,
        current_chapter=chapters[-1] if chapters else None)
