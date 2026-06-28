"""Layer 6 orchestrator — the background proactive cycle (architecture doc §8).

Runs every 30 minutes, independent of the user-initiated pipeline. Recomputes queue
priorities, expires stale items, then evaluates the top candidates through SC-2 → SC-3 →
(if cleared) SC-4. At most one message is sent per cycle; the daily cap is enforced by the
gate as the in-cycle send counter increments.

Hard rules honored here (architecture doc §11, §13):
- Nothing is sent that SC-4 did not generate and validate — no pre-written fallbacks.
- A gate error is treated as blocking (the item is deferred), never as a send.
- The default is silence: only items that clear every gate AND produce a valid message send.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.layer6_proactivity import message_generator
from backend.layer6_proactivity.initiative_classifier import classify_initiative
from backend.layer6_proactivity.queue_manager import ProactiveQueueManager
from backend.layer6_proactivity.schemas import (
    GateAction,
    GateDecision,
    ItemStatus,
    ProactiveContext,
    ProactiveEngineOutput,
    ProactiveItem,
    UserTimingContext,
)
from backend.layer6_proactivity.timing_gate import evaluate_timing_gate

_POLL_INTERVAL = timedelta(minutes=30)
_CANDIDATE_LIMIT = 10


def _default_context(item: ProactiveItem) -> ProactiveContext:
    return ProactiveContext(
        source_memory_summaries=[item.content_basis] if item.content_basis else [],
        persona_instruction="a warm, thoughtful companion",
        bes_trend_description="",
    )


def run_proactive_cycle(
    queue_manager: ProactiveQueueManager,
    user_context: UserTimingContext,
    bes_trend: str = "stable",
    relationship_stage: str = "developing",
    session_gap_days: int = 0,
    now: Optional[datetime] = None,
    user_id: str = "",
    llm_fn: Optional[Callable[[str], str]] = None,
    context_builder: Optional[Callable[[ProactiveItem], ProactiveContext]] = None,
    memory_strength_fn: Optional[Callable[[str], float]] = None,
) -> ProactiveEngineOutput:
    """Run one Layer 6 evaluation cycle and return the audit output (architecture doc §8)."""
    now = now or datetime.utcnow()
    context_builder = context_builder or _default_context

    out = ProactiveEngineOutput(cycle_timestamp=now, next_evaluation_at=now + _POLL_INTERVAL)

    # Refresh priorities and retire expired items.
    queue_manager.recompute_all(bes_trend, now, session_gap_days)
    for expired in queue_manager.expire(now):
        out.messages_suppressed.append((expired.item_id, "item_expired"))

    candidates = queue_manager.top_candidates(n=_CANDIDATE_LIMIT)
    if candidates:
        out.highest_priority_item = candidates[0]

    for item in candidates:
        out.total_items_evaluated += 1
        classified = classify_initiative(item, bes_trend, relationship_stage, session_gap_days)

        # A gate error is treated as blocking, never as a send (§11).
        try:
            decision = evaluate_timing_gate(
                item, classified, user_context, now=now, memory_strength_fn=memory_strength_fn
            )
        except Exception:
            decision = GateDecision(action=GateAction.DEFER.value, reason="gate_error")

        item.last_evaluated_at = now
        out.gate_decisions.append((item.item_id, decision.reason))

        if decision.action == GateAction.SEND_NOW.value:
            payload = message_generator.generate_proactive_message(
                item, classified, context_builder(item), user_id=user_id, llm_fn=llm_fn, now=now
            )
            if payload is not None:
                item.status = ItemStatus.SENT.value
                item.sent_at = now
                out.messages_sent.append(payload)
                # Enforce the 1/day cap for the rest of this cycle via the gate.
                user_context.proactive_messages_sent_today += 1
            else:
                # §11: generation failed → send nothing; defer the item.
                item.status = ItemStatus.DEFERRED.value
                item.send_attempt_count += 1
                out.messages_deferred.append((item.item_id, "generation_failed"))

        elif decision.action == GateAction.DEFER.value:
            item.status = ItemStatus.DEFERRED.value
            item.send_attempt_count += 1
            out.messages_deferred.append((item.item_id, decision.reason))

        else:  # suppress
            item.status = ItemStatus.SUPPRESSED.value
            out.messages_suppressed.append((item.item_id, decision.reason))

    out.queue_size = len(queue_manager.items)
    return out
