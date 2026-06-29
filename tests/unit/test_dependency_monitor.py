"""Tests for SC-4 Dependency Monitor (architecture doc §6)."""

from backend.layer11_safety import dependency_monitor as dm
from backend.layer11_safety.schemas import DependencyScore


def _detector(*firing_ids):
    fired = set(firing_ids)
    return lambda indicator: indicator.indicator_id in fired


def _score(detector=None, previous=None):
    return dm.compute_dependency_score("u1", indicator_detector=detector or (lambda i: False),
                                       previous_score=previous)


# ── Indicator catalog (§6.2) ─────────────────────────────────────────────────
def test_indicator_catalog_matches_enumerated_set():
    # The doc §6.2 enumerates 14 indicators (SS×4, AE×4, EI×3, UP×3); its prose summary's
    # "15" is an off-by-one. We implement the enumerated set.
    assert len(dm.DEPENDENCY_INDICATORS) == 14


# ── Score computation (§6.3) ─────────────────────────────────────────────────
def test_no_signals_is_healthy():
    s = _score()
    assert isinstance(s, DependencyScore)
    assert s.score == 0.0 and s.tier == "healthy"
    assert s.recommended_action == "no_action"


def test_score_is_weighted_fraction():
    total = sum(i.weight for i in dm.DEPENDENCY_INDICATORS)
    s = _score(detector=_detector("SS_01"))      # weight 0.20
    assert abs(s.score - (0.20 / total)) < 1e-9


def test_dominant_signals_top_three_by_weight():
    s = _score(detector=_detector("UP_01", "SS_01", "SS_04", "AE_02"))  # 0.08,0.20,0.20,0.10
    assert s.dominant_signals[:2] == ["SS_01", "SS_04"] or s.dominant_signals[:2] == ["SS_04", "SS_01"]
    assert "UP_01" not in s.dominant_signals      # lowest weight drops out of top 3


# ── Tier thresholds (§6.3) ───────────────────────────────────────────────────
def test_tier_for_score_boundaries():
    assert dm.tier_for_score(0.10) == "healthy"
    assert dm.tier_for_score(0.40) == "watchful"
    assert dm.tier_for_score(0.60) == "concerning"
    assert dm.tier_for_score(0.80) == "intervention"
    assert dm.tier_for_score(1.00) == "intervention"   # inclusive top bound


# ── Trend (§6.3) ─────────────────────────────────────────────────────────────
def test_trend_worsening():
    prev = DependencyScore(user_id="u1", score=0.10)
    s = _score(detector=_detector("SS_01", "SS_04"), previous=prev)
    assert s.trend == "worsening"


def test_trend_improving():
    prev = DependencyScore(user_id="u1", score=0.90)
    s = _score(detector=_detector("SS_01"), previous=prev)
    assert s.trend == "improving"


# ── Interventions (§6.4) ─────────────────────────────────────────────────────
def test_intervention_script_for_intervention_tier():
    script = dm.get_intervention("intervention")
    assert "message_template" in script and script["message_template"]


def test_watchful_action_is_subtle_reinforcement():
    assert dm.DEPENDENCY_TIER_ACTIONS["watchful"] == "subtle_human_reinforcement"
