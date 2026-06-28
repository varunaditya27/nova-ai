"""Tests for SC-3 Timing & Delivery Gate (architecture doc §5)."""

from datetime import datetime, timedelta

from backend.layer6_proactivity import timing_gate as tg
from backend.layer6_proactivity.schemas import (
    ClassifiedInitiative,
    GateAction,
    InitiativeType,
    ProactiveItem,
    ProactiveItemType,
    UserTimingContext,
)

NOW = datetime(2026, 6, 28, 14, 0, 0)


def _item(item_type=ProactiveItemType.THREAD_FOLLOW_UP.value, **kw):
    base = dict(item_type=item_type,
                content_basis="User mentioned an interview on Tuesday at the new company.",
                earliest_send_time=NOW - timedelta(hours=1),
                expiry_time=NOW + timedelta(days=10), send_attempt_count=0)
    base.update(kw)
    return ProactiveItem(**base)


def _classified(initiative_type=InitiativeType.CURIOUS_FOLLOW_UP.value):
    return ClassifiedInitiative(initiative_type=initiative_type)


def _ctx(**kw):
    base = dict(circadian_band="afternoon", minutes_since_last_message=999,
                hours_since_last_proactive_message=9999.0, proactive_messages_sent_today=0,
                bes_trend="stable", last_session_crisis_flag=False, last_session_end_valence=0.0,
                relationship_stage="developing", tie_strength=0.5, user_preferences={},
                is_in_quiet_period=False)
    base.update(kw)
    return UserTimingContext(**base)


def _gate(item=None, classified=None, ctx=None, **mem):
    return tg.evaluate_timing_gate(item or _item(), classified or _classified(),
                                   ctx or _ctx(), now=NOW, **mem)


# ── Baseline: everything clear → send (§5.1 inversion) ───────────────────────
def test_all_gates_pass_sends_now():
    d = _gate()
    assert d.action == GateAction.SEND_NOW.value
    assert d.reason == "all_gates_passed"


# ── Block group 1: hard temporal (§5.2) ──────────────────────────────────────
def test_before_earliest_send_defers():
    d = _gate(item=_item(earliest_send_time=NOW + timedelta(hours=2)))
    assert d.action == GateAction.DEFER.value and d.reason == "before_earliest_send_time"


def test_past_expiry_suppresses():
    d = _gate(item=_item(expiry_time=NOW - timedelta(hours=1)))
    assert d.action == GateAction.SUPPRESS.value and d.reason == "item_expired"


def test_late_night_defers():
    d = _gate(ctx=_ctx(circadian_band="late_night"))
    assert d.action == GateAction.DEFER.value and d.reason == "late_night_block"


def test_active_session_defers():
    d = _gate(ctx=_ctx(minutes_since_last_message=2))
    assert d.action == GateAction.DEFER.value and d.reason == "active_session"


def test_daily_cap_defers():
    d = _gate(ctx=_ctx(proactive_messages_sent_today=1))
    assert d.action == GateAction.DEFER.value and d.reason == "daily_cap_reached"


def test_min_gap_defers():
    d = _gate(ctx=_ctx(hours_since_last_proactive_message=10.0,
                       last_proactive_sent_at=NOW - timedelta(hours=10)))
    assert d.action == GateAction.DEFER.value and d.reason == "min_gap_not_met"


# ── Block group 2: emotional (§5.2) ──────────────────────────────────────────
def test_post_crisis_defers_non_wellbeing():
    d = _gate(ctx=_ctx(last_session_crisis_flag=True))
    assert d.action == GateAction.DEFER.value and d.reason == "post_crisis_sensitivity"


def test_post_crisis_allows_wellbeing_check():
    d = _gate(item=_item(ProactiveItemType.WELLBEING_CHECK.value),
              ctx=_ctx(last_session_crisis_flag=True))
    assert d.action == GateAction.SEND_NOW.value


def test_bes_deteriorating_suppresses_non_wellbeing():
    d = _gate(ctx=_ctx(bes_trend="deteriorating"))
    assert d.action == GateAction.SUPPRESS.value and d.reason == "bes_deteriorating_non_wellbeing"


def test_high_distress_defers_celebratory():
    d = _gate(classified=_classified(InitiativeType.CELEBRATORY_FOLLOW_UP.value),
              ctx=_ctx(last_session_end_valence=-0.8))
    assert d.action == GateAction.DEFER.value and d.reason == "recent_high_distress"


# ── Block group 3: relationship (§5.2) ───────────────────────────────────────
def test_new_relationship_suppresses():
    d = _gate(ctx=_ctx(relationship_stage="new"))
    assert d.action == GateAction.SUPPRESS.value and d.reason == "relationship_too_new"


def test_acquaintance_restricts_type():
    d = _gate(item=_item(ProactiveItemType.WELLBEING_CHECK.value),
              ctx=_ctx(relationship_stage="acquaintance"))
    assert d.action == GateAction.DEFER.value and d.reason == "relationship_stage_restricts_type"


def test_acquaintance_allows_thread_follow_up():
    d = _gate(item=_item(ProactiveItemType.THREAD_FOLLOW_UP.value),
              ctx=_ctx(relationship_stage="acquaintance"))
    assert d.action == GateAction.SEND_NOW.value


def test_concerned_checkin_low_tie_strength_suppresses():
    d = _gate(item=_item(ProactiveItemType.EMOTIONAL_CHECK_IN.value),
              classified=_classified(InitiativeType.CONCERNED_CHECK_IN.value),
              ctx=_ctx(tie_strength=0.2))
    assert d.action == GateAction.SUPPRESS.value


# ── Block group 4: preferences (§5.2) ────────────────────────────────────────
def test_user_disabled_type_suppresses():
    d = _gate(ctx=_ctx(user_preferences={"proactive_thread_follow_up_enabled": False}))
    assert d.action == GateAction.SUPPRESS.value


def test_user_disabled_all_suppresses():
    d = _gate(ctx=_ctx(user_preferences={"proactive_all_enabled": False}))
    assert d.action == GateAction.SUPPRESS.value and d.reason == "user_disabled_all_proactive"


def test_quiet_period_defers():
    d = _gate(ctx=_ctx(is_in_quiet_period=True, quiet_period_end=NOW + timedelta(hours=8)))
    assert d.action == GateAction.DEFER.value and d.reason == "user_quiet_period"


# ── Block group 5: quality (§5.2) ────────────────────────────────────────────
def test_weak_source_memory_suppresses():
    d = _gate(item=_item(source_memory_ids=["m1"]), memory_strength_fn=lambda mid: 0.1)
    assert d.action == GateAction.SUPPRESS.value and d.reason == "source_memory_too_weak"


def test_vague_content_basis_suppresses():
    d = _gate(item=_item(content_basis="too short"))
    assert d.action == GateAction.SUPPRESS.value and d.reason == "content_basis_too_vague"


def test_max_defer_attempts_suppresses():
    d = _gate(item=_item(send_attempt_count=5))
    assert d.action == GateAction.SUPPRESS.value and d.reason == "max_defer_attempts_reached"
