"""SC-3 — Timing & Delivery Gate (architecture doc §5).

The primary safeguard of Layer 6. Makes the final binary decision: send now, or not.
The gate defaults to *do not send* — every condition is a reason to suppress/defer, never
a reason to send. The only path to ``send_now`` is clearing every blocking condition.
This inversion makes the gate naturally conservative and extensible (§5.1).

Deterministic, no I/O on the hot path. The only external lookup — source-memory strength
(B5.1) — is an injected ``memory_strength_fn`` (skipped when absent), so the gate runs
offline. Per §11, any unexpected error in a condition should be treated as blocking by the
caller (the orchestrator wraps the gate).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.layer6_proactivity.schemas import (
    ClassifiedInitiative,
    GateAction,
    GateDecision,
    InitiativeType,
    ProactiveItem,
    ProactiveItemType,
    UserTimingContext,
)

_MIN_GAP_HOURS = 48
_ACTIVE_SESSION_MINUTES = 5
_HIGH_DISTRESS_VALENCE = -0.7
_CONCERNED_TIE_FLOOR = 0.35
_MEMORY_STRENGTH_FLOOR = 0.15
_MIN_CONTENT_BASIS_LEN = 20
_MAX_DEFER_ATTEMPTS = 5

_ACQUAINTANCE_ALLOWED = {
    ProactiveItemType.THREAD_FOLLOW_UP.value,
    ProactiveItemType.UPCOMING_DATE_REMINDER.value,
}
_BES_DETERIORATING_ALLOWED = {
    ProactiveItemType.EMOTIONAL_CHECK_IN.value,
    ProactiveItemType.WELLBEING_CHECK.value,
}
_HIGH_DISTRESS_BLOCKED_INITIATIVES = {
    InitiativeType.CELEBRATORY_FOLLOW_UP.value,
    InitiativeType.GENTLE_NUDGE.value,
}


def _defer(reason: str, retry_after: Optional[datetime] = None) -> GateDecision:
    return GateDecision(action=GateAction.DEFER.value, reason=reason, retry_after=retry_after)


def _suppress(reason: str) -> GateDecision:
    return GateDecision(action=GateAction.SUPPRESS.value, reason=reason)


def evaluate_timing_gate(
    item: ProactiveItem,
    classified: ClassifiedInitiative,
    user_context: UserTimingContext,
    now: Optional[datetime] = None,
    memory_strength_fn: Optional[Callable[[str], float]] = None,
) -> GateDecision:
    """Return the first blocking decision, or ``send_now`` if nothing blocks (§5.2)."""
    now = now or datetime.utcnow()
    ctx = user_context

    # ── Block group 1: hard temporal ─────────────────────────────────────────
    if item.earliest_send_time and now < item.earliest_send_time:
        return _defer("before_earliest_send_time", retry_after=item.earliest_send_time)
    if item.expiry_time and now > item.expiry_time:
        return _suppress("item_expired")
    if ctx.circadian_band == "late_night":
        return _defer("late_night_block")
    if ctx.minutes_since_last_message < _ACTIVE_SESSION_MINUTES:
        return _defer("active_session", retry_after=now + timedelta(hours=1))
    if ctx.proactive_messages_sent_today >= 1:
        return _defer("daily_cap_reached")
    if ctx.hours_since_last_proactive_message < _MIN_GAP_HOURS:
        retry = (ctx.last_proactive_sent_at + timedelta(hours=_MIN_GAP_HOURS)
                 if ctx.last_proactive_sent_at else None)
        return _defer("min_gap_not_met", retry_after=retry)

    # ── Block group 2: emotional state ───────────────────────────────────────
    if ctx.last_session_crisis_flag and item.item_type != ProactiveItemType.WELLBEING_CHECK.value:
        return _defer("post_crisis_sensitivity", retry_after=now + timedelta(hours=24))
    if ctx.bes_trend == "deteriorating" and item.item_type not in _BES_DETERIORATING_ALLOWED:
        return _suppress("bes_deteriorating_non_wellbeing")
    if (ctx.last_session_end_valence < _HIGH_DISTRESS_VALENCE
            and classified.initiative_type in _HIGH_DISTRESS_BLOCKED_INITIATIVES):
        return _defer("recent_high_distress", retry_after=now + timedelta(hours=36))

    # ── Block group 3: relationship state ────────────────────────────────────
    if ctx.relationship_stage == "new":
        return _suppress("relationship_too_new")
    if ctx.relationship_stage == "acquaintance" and item.item_type not in _ACQUAINTANCE_ALLOWED:
        return _defer("relationship_stage_restricts_type")
    if (classified.initiative_type == InitiativeType.CONCERNED_CHECK_IN.value
            and ctx.tie_strength < _CONCERNED_TIE_FLOOR):
        return _suppress("tie_strength_below_threshold_for_concerned")

    # ── Block group 4: user preferences ──────────────────────────────────────
    pref_key = f"proactive_{item.item_type}_enabled"
    if not ctx.user_preferences.get(pref_key, True):
        return _suppress(f"user_disabled_{item.item_type}")
    if not ctx.user_preferences.get("proactive_all_enabled", True):
        return _suppress("user_disabled_all_proactive")
    if ctx.is_in_quiet_period:
        return _defer("user_quiet_period", retry_after=ctx.quiet_period_end)

    # ── Block group 5: quality and coherence ─────────────────────────────────
    if item.source_memory_ids and memory_strength_fn is not None:
        min_strength = min(memory_strength_fn(mid) for mid in item.source_memory_ids)
        if min_strength < _MEMORY_STRENGTH_FLOOR:
            return _suppress("source_memory_too_weak")
    if len(item.content_basis) < _MIN_CONTENT_BASIS_LEN:
        return _suppress("content_basis_too_vague")
    if item.send_attempt_count >= _MAX_DEFER_ATTEMPTS:
        return _suppress("max_defer_attempts_reached")

    # ── No blocks: approve ───────────────────────────────────────────────────
    return GateDecision(action=GateAction.SEND_NOW.value, reason="all_gates_passed",
                        approved_at=now)
