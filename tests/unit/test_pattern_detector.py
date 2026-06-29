"""Tests for SC-3 pattern detection (architecture doc §5.3)."""

from datetime import date, timedelta

from backend.layer10_longitudinal import progress_tracker as pt
from backend.layer10_longitudinal.schemas import EmotionalRecord, EpisodicRecord

START = date(2025, 1, 6)        # a Monday


def _emo(d, valence, emotion="neutral"):
    return EmotionalRecord(date=START + timedelta(days=d), valence=valence, primary_emotion=emotion)


def _ep(d, topics):
    return EpisodicRecord(episode_id=f"e{d}", date=START + timedelta(days=d), topics=topics)


def test_detects_emotional_cycle_on_recurring_low_day():
    # 8 Mondays at low valence; other days neutral-positive.
    recs = []
    for w in range(8):
        recs.append(_emo(w * 7, -0.6))          # Monday dip
        recs.append(_emo(w * 7 + 2, 0.3))       # Wednesday
        recs.append(_emo(w * 7 + 4, 0.3))       # Friday
    patterns = pt.detect_behavioral_patterns(recs, [], [])
    cycles = [p for p in patterns if p.pattern_type == "emotional_cycle"]
    assert cycles and "Monday" in cycles[0].description


def test_requires_minimum_occurrences():
    # Only 2 Mondays — below the 3-occurrence floor → not a pattern.
    recs = [_emo(0, -0.7), _emo(7, -0.7), _emo(2, 0.3), _emo(4, 0.3)]
    cycles = [p for p in pt.detect_behavioral_patterns(recs, [], [])
              if p.pattern_type == "emotional_cycle"]
    assert cycles == []


def test_detects_topic_recurrence_over_weeks():
    eps = [_ep(w * 7, ["work_stress"]) for w in range(8)]
    patterns = pt.detect_behavioral_patterns([], [], eps)
    topics = [p for p in patterns if p.pattern_type == "topic_recurrence"]
    assert topics and "work_stress" in topics[0].description


def test_low_confidence_patterns_filtered():
    # A topic recurring only 3 times over 4 weeks → confidence 0.3 < 0.65 default → filtered.
    eps = [_ep(0, ["x"]), _ep(14, ["x"]), _ep(28, ["x"])]
    topics = [p for p in pt.detect_behavioral_patterns([], [], eps)
              if p.pattern_type == "topic_recurrence"]
    assert topics == []


def test_pattern_has_dates_and_count():
    eps = [_ep(w * 7, ["work_stress"]) for w in range(8)]
    p = [x for x in pt.detect_behavioral_patterns([], [], eps)
         if x.pattern_type == "topic_recurrence"][0]
    assert p.occurrence_count == 8
    assert p.first_detected_date == START
    assert p.last_observed_date == START + timedelta(days=49)
