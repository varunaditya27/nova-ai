"""Tests for the Layer 6 orchestrator / ProactiveEngineOutput (architecture doc §8, §11)."""

from datetime import datetime, timedelta

from backend.layer6_proactivity import engine
from backend.layer6_proactivity import queue_manager as qm
from backend.layer6_proactivity.schemas import (
    ItemStatus,
    ProactiveEngineOutput,
    ProactiveItem,
    ProactiveItemType,
    UserTimingContext,
)

NOW = datetime(2026, 6, 28, 14, 0, 0)


def _clear_item(**kw):
    base = dict(item_type=ProactiveItemType.THREAD_FOLLOW_UP.value,
                content_basis="User mentioned a presentation on Tuesday at work.",
                content_basis_valence=0.5,
                base_priority=0.8, current_priority=0.8,
                earliest_send_time=NOW - timedelta(hours=1),
                optimal_send_window=(NOW - timedelta(days=1), NOW + timedelta(days=1)),
                expiry_time=NOW + timedelta(days=5), status=ItemStatus.PENDING.value)
    base.update(kw)
    return ProactiveItem(**base)


def _ctx(**kw):
    base = dict(circadian_band="afternoon", minutes_since_last_message=999,
                hours_since_last_proactive_message=9999.0, proactive_messages_sent_today=0,
                bes_trend="stable", relationship_stage="developing", tie_strength=0.5,
                user_preferences={})
    base.update(kw)
    return UserTimingContext(**base)


def _good_llm(prompt):
    return "Hey — how did the presentation end up going on Tuesday?"


def _run(mgr, ctx=None, llm_fn=_good_llm):
    return engine.run_proactive_cycle(
        mgr, ctx or _ctx(), bes_trend="stable", relationship_stage="developing",
        session_gap_days=2, now=NOW, user_id="u1", llm_fn=llm_fn)


# ── Happy path: one message sent (§8) ────────────────────────────────────────
def test_cycle_sends_one_when_clear():
    mgr = qm.ProactiveQueueManager()
    mgr.add_item(_clear_item())
    out = _run(mgr)
    assert isinstance(out, ProactiveEngineOutput)
    assert len(out.messages_sent) == 1
    assert "presentation" in out.messages_sent[0].message_text.lower()
    assert mgr.items[0].status == ItemStatus.SENT.value


# ── All blocked → nothing sent (§13 default silence) ─────────────────────────
def test_cycle_sends_nothing_when_blocked():
    mgr = qm.ProactiveQueueManager()
    mgr.add_item(_clear_item())
    out = engine.run_proactive_cycle(
        mgr, _ctx(relationship_stage="new"), bes_trend="stable",
        relationship_stage="new", session_gap_days=2, now=NOW, llm_fn=_good_llm)
    assert out.messages_sent == []
    assert len(out.messages_suppressed) == 1


# ── Daily cap: only one send per cycle (§3.4, §13) ───────────────────────────
def test_cycle_respects_daily_cap():
    mgr = qm.ProactiveQueueManager()
    mgr.add_item(_clear_item())
    mgr.add_item(_clear_item())
    out = _run(mgr)
    assert len(out.messages_sent) == 1
    assert any(reason == "daily_cap_reached" for _, reason in out.messages_deferred)


# ── §11 hard rule: never send an ungenerated/invalid message ─────────────────
def test_cycle_no_send_on_generation_failure():
    mgr = qm.ProactiveQueueManager()
    mgr.add_item(_clear_item())
    out = _run(mgr, llm_fn=lambda p: "Just checking in, wanted to reach out!")  # always robotic
    assert out.messages_sent == []
    assert any("generation_failed" == reason for _, reason in out.messages_deferred)


def test_cycle_no_send_without_llm():
    mgr = qm.ProactiveQueueManager()
    mgr.add_item(_clear_item())
    out = _run(mgr, llm_fn=None)
    assert out.messages_sent == []


# ── Audit (§8) ───────────────────────────────────────────────────────────────
def test_cycle_audit_fields_populated():
    mgr = qm.ProactiveQueueManager()
    mgr.add_item(_clear_item())
    out = _run(mgr)
    assert out.total_items_evaluated >= 1
    assert out.gate_decisions
    assert out.next_evaluation_at == NOW + timedelta(minutes=30)
    assert out.cycle_timestamp == NOW
