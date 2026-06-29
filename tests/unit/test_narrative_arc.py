"""Tests for SC-1 Narrative Arc — chapter boundaries + emotional arc (architecture doc §3.2-§3.4)."""

from datetime import date, timedelta

from backend.layer10_longitudinal import narrative_arc as na
from backend.layer10_longitudinal.schemas import (
    EmotionalArcSummary,
    EmotionalRecord,
    LifeEvent,
    NarrativeArc,
)

START = date(2025, 1, 1)


def _event(days, category="career_transition", title="New job", sig=0.9):
    return LifeEvent(event_id=f"e{days}", user_id="u1", title=title, category=category,
                     event_date=START + timedelta(days=days), significance_score=sig)


def _emo(days, valence, arousal=0.5, emotion="neutral"):
    return EmotionalRecord(date=START + timedelta(days=days), valence=valence, arousal=arousal,
                           primary_emotion=emotion)


# ── Chapter boundary detection (§3.4) ────────────────────────────────────────
def test_life_event_creates_chapter_boundary():
    bounds = na.detect_chapter_boundaries([_event(60)], now=START + timedelta(days=120))
    assert (START + timedelta(days=60)) in bounds


def test_non_boundary_category_ignored():
    bounds = na.detect_chapter_boundaries([_event(60, category="other")],
                                          now=START + timedelta(days=120))
    assert bounds == []


def test_min_chapter_duration_suppresses_micro_chapters():
    # Two boundary events 10 days apart — the second is within the 21-day floor → dropped.
    bounds = na.detect_chapter_boundaries(
        [_event(60), _event(70, title="Promotion")], now=START + timedelta(days=120))
    assert bounds == [START + timedelta(days=60)]


# ── Emotional arc (§3.2) ─────────────────────────────────────────────────────
def test_emotional_arc_improving():
    recs = [_emo(d, v) for d, v in [(0, -0.5), (10, -0.2), (20, 0.2), (30, 0.6)]]
    assert na.compute_emotional_arc(recs).trajectory == "improving"


def test_emotional_arc_declining():
    recs = [_emo(d, v) for d, v in [(0, 0.6), (10, 0.2), (20, -0.2), (30, -0.5)]]
    assert na.compute_emotional_arc(recs).trajectory == "declining"


def test_emotional_arc_recovering():
    recs = [_emo(d, v) for d, v in [(0, 0.3), (10, -0.6), (20, -0.4), (30, 0.4)]]
    assert na.compute_emotional_arc(recs).trajectory == "recovering"


def test_emotional_arc_reports_dominant_emotion():
    recs = [_emo(0, 0.1, emotion="anxious"), _emo(5, 0.1, emotion="anxious"),
            _emo(10, 0.1, emotion="calm")]
    assert na.compute_emotional_arc(recs).dominant_emotion == "anxious"


def test_emotional_arc_empty_is_graceful():
    arc = na.compute_emotional_arc([])
    assert isinstance(arc, EmotionalArcSummary)


# ── Arc assembly (§3.2) ──────────────────────────────────────────────────────
def test_build_arc_splits_into_chapters_at_boundaries():
    arc = na.build_narrative_arc(
        user_id="u1", arc_start_date=START, life_events=[_event(60)],
        emotional_records=[_emo(d, 0.1) for d in range(0, 120, 10)],
        now=START + timedelta(days=120))
    assert isinstance(arc, NarrativeArc)
    assert len(arc.chapters) == 2
    assert arc.current_chapter.is_current is True
    assert arc.current_chapter.end_date is None


def test_build_arc_with_no_events_is_single_ongoing_chapter():
    arc = na.build_narrative_arc(user_id="u1", arc_start_date=START, life_events=[],
                                 emotional_records=[_emo(0, 0.1)], now=START + timedelta(days=30))
    assert len(arc.chapters) == 1 and arc.chapters[0].is_current is True


def test_chapter_title_reflects_life_event():
    title = na.assign_chapter_title([_event(0, title="Started at Infosys")], themes=[])
    assert isinstance(title, str) and title
