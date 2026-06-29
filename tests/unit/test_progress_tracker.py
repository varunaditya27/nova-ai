"""Tests for SC-3 Progress Tracker — snapshot metrics + domain balance (architecture doc §5.2)."""

from datetime import date, timedelta
from types import SimpleNamespace

from backend.layer10_longitudinal import progress_tracker as pt
from backend.layer10_longitudinal.schemas import (
    EmotionalRecord,
    EpisodicRecord,
    ProgressSnapshot,
    SessionRecord,
)

NOW = date(2025, 6, 1)


def _emo(days_ago, valence):
    return EmotionalRecord(date=NOW - timedelta(days=days_ago), valence=valence)


def _goal(status):
    return SimpleNamespace(status=status)


def _ep(topics):
    return EpisodicRecord(episode_id="e", date=NOW, topics=topics)


def _snapshot(emo=None, sessions=None, goals=None, eps=None):
    return pt.compute_progress_snapshot(
        user_id="u1", as_of_date=NOW, emotional_records=emo or [], sessions=sessions or [],
        goals=goals or [], episodic_records=eps or [])


# ── Goal metrics (§5.2) ──────────────────────────────────────────────────────
def test_achievement_rate():
    s = _snapshot(goals=[_goal("achieved"), _goal("achieved"), _goal("abandoned")])
    assert isinstance(s, ProgressSnapshot)
    assert abs(s.achievement_rate_lifetime - (2 / 3)) < 1e-9
    assert s.goals_achieved_lifetime == 2


# ── Emotional metrics (§5.2) ─────────────────────────────────────────────────
def test_avg_valence_4w_window():
    emo = [_emo(2, 0.4), _emo(10, 0.2), _emo(40, -0.9)]   # the -0.9 is outside 28d
    s = _snapshot(emo=emo)
    assert abs(s.avg_valence_4w - 0.3) < 1e-9


def test_valence_trend_improving():
    emo = [_emo(d, -0.4) for d in range(30, 60)] + [_emo(d, 0.4) for d in range(0, 14)]
    assert _snapshot(emo=emo).valence_trend_short == "improving"


def test_crisis_frequency_counts_recent_crisis_sessions():
    sessions = [SessionRecord(session_id="s1", date=NOW - timedelta(days=5), crisis_mode_active=True),
                SessionRecord(session_id="s2", date=NOW - timedelta(days=10))]
    assert _snapshot(sessions=sessions).crisis_event_frequency > 0


def test_resilience_score_in_unit_interval():
    s = _snapshot(emo=[_emo(d, 0.3) for d in range(0, 30)])
    assert 0.0 <= s.resilience_score <= 1.0


# ── Domain balance (§5.2) ────────────────────────────────────────────────────
def test_domain_balance_dominant_and_neglected():
    # 15 career + 1 health → health weight ≈ 0.0625, below the 0.08 neglected floor.
    eps = [_ep(["career"]) for _ in range(15)] + [_ep(["health"])]
    bal = pt.compute_domain_balance(eps)
    assert bal.dominant_domain == "career"
    assert "health" in bal.neglected_domains


def test_domain_balance_score_higher_when_diversified():
    concentrated = pt.compute_domain_balance([_ep(["career"]) for _ in range(10)])
    diversified = pt.compute_domain_balance(
        [_ep(["career"]), _ep(["health"]), _ep(["relationships"]), _ep(["learning"])])
    assert diversified.balance_score > concentrated.balance_score


def test_empty_inputs_are_graceful():
    s = _snapshot()
    assert isinstance(s, ProgressSnapshot) and s.achievement_rate_lifetime == 0.0
