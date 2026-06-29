"""Tests for SC-2 Weekly Summary Engine (architecture doc §4)."""

from datetime import date, datetime, timedelta

from backend.layer10_longitudinal import weekly_summary as ws
from backend.layer10_longitudinal.schemas import (
    EmotionalRecord,
    EpisodicRecord,
    SessionRecord,
    WeeklyEmotionalSummary,
    WeeklySummary,
)

WEEK_START = date(2025, 6, 2)        # Monday
WEEK_END = date(2025, 6, 8)          # Sunday


def _sess(day, dur=20.0, disc=0, crisis=False):
    return SessionRecord(session_id=f"s{day}", date=WEEK_START + timedelta(days=day),
                         duration_mins=dur, self_disclosure_events=disc, crisis_mode_active=crisis)


def _emo(day, valence, emotion="neutral", intensity=0.4):
    return EmotionalRecord(date=WEEK_START + timedelta(days=day), valence=valence,
                           primary_emotion=emotion, emotional_intensity=intensity)


def _ep(day, importance=0.5, topics=None, title="chat"):
    return EpisodicRecord(episode_id=f"e{day}", date=WEEK_START + timedelta(days=day),
                          importance_score=importance, topics=topics or [], title=title)


def _gen(sessions, emo=None, eps=None, goals=None, prev=None, baseline=None, llm=None):
    return ws.generate_weekly_summary(
        user_id="u1", week_start=WEEK_START, week_end=WEEK_END,
        episodic_records=eps or [], emotional_records=emo or [], sessions=sessions,
        goals=goals or [], previous_week_summary=prev, baseline_records=baseline or [],
        llm_fn=llm, now=datetime(2025, 6, 8, 20, 0))


# ── Aggregation (§4.3) ───────────────────────────────────────────────────────
def test_session_count_and_dates():
    s = _gen([_sess(0), _sess(2), _sess(5)])
    assert s.session_count == 3 and len(s.session_dates) == 3


def test_returns_weekly_summary_object():
    assert isinstance(_gen([_sess(0), _sess(1)]), WeeklySummary)


# ── Emotional summary (§4.2) ─────────────────────────────────────────────────
def test_avg_valence_computed():
    s = _gen([_sess(0), _sess(1)], emo=[_emo(0, 0.2), _emo(1, 0.4)])
    assert abs(s.emotional_summary.avg_valence - 0.3) < 1e-9


def test_compared_to_previous_week_better():
    prev = WeeklySummary(user_id="u1", week_start_date=WEEK_START - timedelta(days=7),
                         week_end_date=WEEK_START - timedelta(days=1))
    prev.emotional_summary = WeeklyEmotionalSummary(avg_valence=-0.3)
    s = _gen([_sess(0), _sess(1)], emo=[_emo(0, 0.3), _emo(1, 0.4)], prev=prev)
    assert s.emotional_summary.compared_to_previous_week == "better"


def test_compared_to_baseline_below():
    baseline = [_emo(-d, 0.5) for d in range(1, 10)]
    s = _gen([_sess(0), _sess(1)], emo=[_emo(0, -0.4), _emo(1, -0.3)], baseline=baseline)
    assert s.emotional_summary.compared_to_baseline == "below_baseline"


# ── Topics (§4.3 step 3) ─────────────────────────────────────────────────────
def test_primary_topics_extracted_by_frequency():
    eps = [_ep(0, topics=["work", "stress"]), _ep(1, topics=["work"]), _ep(2, topics=["family"])]
    s = _gen([_sess(0), _sess(1), _sess(2)], eps=eps)
    assert s.primary_topics[0] == "work"


def test_most_significant_moment_is_highest_importance():
    eps = [_ep(0, importance=0.4, title="A"), _ep(1, importance=0.9, title="B")]
    s = _gen([_sess(0), _sess(1)], eps=eps)
    assert s.most_emotionally_significant_moment.title == "B"


# ── Min data threshold (§11) ─────────────────────────────────────────────────
def test_too_few_sessions_flags_insufficient_data():
    s = _gen([_sess(0)])           # only 1 session
    assert s.minimum_data_threshold_met is False


# ── Narrative (§4.3 step 7) ──────────────────────────────────────────────────
def test_narrative_uses_llm_when_available():
    s = _gen([_sess(0), _sess(1)], emo=[_emo(0, 0.3)],
             llm=lambda p: {"summary": "A steady week.", "standout": "Started journaling."})
    assert s.week_narrative == "A steady week."
    assert s.standout_observation == "Started journaling."


def test_narrative_fallback_without_llm_is_grounded():
    s = _gen([_sess(0), _sess(1)], emo=[_emo(0, 0.3)])
    assert s.week_narrative                       # non-empty, factual


# ── Progress metrics for SC-3 (§4.2) ─────────────────────────────────────────
def test_progress_metrics_count_disclosure_and_crisis():
    s = _gen([_sess(0, disc=2), _sess(1, crisis=True)])
    assert s.progress_metrics.self_disclosure_events == 2
    assert s.progress_metrics.crisis_events == 1
