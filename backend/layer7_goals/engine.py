"""Layer 7 orchestrator — the per-message goal pipeline (architecture doc §8).

Wires the synchronous path (SC-2 retrieval → SC-3 inline progress inference → SC-4
accountability decision) and the SC-1 extraction step into a single ``Layer7Output``.

Hard rule (§10): a failure in any Layer 7 component must never block response generation.
The synchronous read path (SC-2 + SC-4) is wrapped so SC-2 failing returns an empty packet
and the response proceeds with no goal reference. SC-1 extraction is asynchronous in
production; here it runs inline only when an extractor LLM is supplied.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer7_goals import goal_extractor, progress_monitor
from backend.layer7_goals.accountability_modifier import decide_goal_reference
from backend.layer7_goals.goal_store import GoalStore
from backend.layer7_goals.schemas import (
    Goal,
    GoalContextPacket,
    GoalSignalEvent,
    GoalSignalStrength,
    GoalStatus,
    Layer7Output,
    ProgressSignalType,
)


def _safe(fn, fallback):
    try:
        return fn()
    except Exception:
        return fallback


def _parse_deadline(raw, now):
    """The extractor LLM's ISO ``deadline_date`` → a datetime; an unparseable or already-past date
    is dropped (a model guessing the wrong year must not create an instantly-overdue goal)."""
    try:
        parsed = datetime.fromisoformat(str(raw)[:10])
    except (TypeError, ValueError):
        return None
    if now.tzinfo is not None:
        parsed = parsed.replace(tzinfo=now.tzinfo)
    return parsed if parsed.date() >= now.date() else None


def run_goal_pipeline(
    message: str,
    goal_store: GoalStore,
    message_id: str = "",
    emotional_state=None,
    conversation_mode: str = "goal_planning",
    relationship_stage: str = "developing",
    similarity_fn: Optional[Callable[[str, str], float]] = None,
    extractor_llm_fn: Optional[Callable[[str], object]] = None,
    now: Optional[datetime] = None,
) -> Layer7Output:
    """Run the synchronous Layer 7 path for one message (architecture doc §2, §8)."""
    now = now or datetime.utcnow()
    out = Layer7Output(cycle_timestamp=now)

    # SC-2: relevant goals (failure → empty, never blocks — §10).
    relevant = _safe(
        lambda: goal_store.get_relevant_goals(
            message, emotional_state=emotional_state, similarity_fn=similarity_fn, now=now
        ),
        [],
    )

    # SC-3: inline progress signal on the top goal.
    progress_signal = None
    if relevant:
        top = relevant[0].goal
        progress_signal = _safe(
            lambda: progress_monitor.classify_signal_for_goal(message, top, similarity_fn), None
        )
        if progress_signal is not None:
            progress_monitor.update_progress_score(top, progress_signal)
            # A completed/abandoned signal is a real terminal status transition, not just a
            # progress-score update -- update_progress_score deliberately leaves status alone
            # ("status handled by the transition rules"), but nothing else in the live per-turn
            # path was actually applying that rule, so every goal stayed "active" forever
            # regardless of what the user said. Layer 10's Year in Review needs status_changed_at
            # to attribute an achievement/abandonment to the right year (docs/POLISH_BACKLOG.md).
            if progress_signal.signal_type in (
                ProgressSignalType.COMPLETED.value, ProgressSignalType.ABANDONED.value
            ) and top.status != progress_signal.signal_type:
                top.status = progress_signal.signal_type
                top.status_changed_at = now
            top.signal_events.append(GoalSignalEvent(
                goal_id=top.goal_id, event_type=progress_signal.signal_type,
                timestamp=now, evidence_text=message,
                confidence=progress_signal.confidence))
            top.momentum_score = progress_monitor.compute_momentum(top.signal_events, now=now)
            top.last_mentioned_at = now
            goal_store.update_goal(top)  # persist progress through the store (store-agnostic)
            out.goals_updated.append(top.goal_id)

    # SC-5 habits: "I went for a run this morning" checks in the best-matching active habit on any
    # relevant goal (unconditional on the top-goal signal above — habits are their own surface).
    if similarity_fn is not None:
        for rel in relevant:
            if _safe(lambda g=rel.goal: progress_monitor.record_habit_check_in(
                    g, message, similarity_fn, now), None) is not None:
                goal_store.update_goal(rel.goal)
                if rel.goal.goal_id not in out.goals_updated:
                    out.goals_updated.append(rel.goal.goal_id)

    # SC-4: accountability decision → GoalContextPacket (failure → no reference).
    packet = _safe(
        lambda: decide_goal_reference(
            relevant, progress_signal, emotional_state, conversation_mode,
            relationship_stage, now=now,
        ),
        GoalContextPacket(should_reference_goal=False),
    )

    # SC-1: extraction (async in production; inline only when an LLM is supplied).
    if extractor_llm_fn is not None:
        active = goal_store.load_by_status([
            GoalStatus.ACTIVE.value, GoalStatus.ON_TRACK.value,
            GoalStatus.AT_RISK.value, GoalStatus.TENTATIVE.value,
        ])
        extraction = _safe(
            lambda: goal_extractor.extract_goal(
                message, message_id=message_id, active_goals=active,
                llm_fn=extractor_llm_fn, similarity_fn=similarity_fn, now=now,
            ),
            None,
        )
        if extraction is not None:
            packet.new_goal_pending = extraction
            if extraction.new_goal_data:
                data = extraction.new_goal_data
                new_goal = Goal(
                    title=data.get("inferred_title", ""),
                    raw_statement=data.get("raw_statement", message),
                    domain=data.get("inferred_domain", "other"),
                    direction=data.get("inferred_direction", "achieve_outcome"),
                    status=GoalStatus.ACTIVE.value,
                    status_changed_at=now,
                    confidence_at_creation=extraction.confidence,
                    signal_strength=extraction.signal_strength or GoalSignalStrength.EXPLICIT_STATED.value,
                    emotional_weight=float(data.get("emotional_weight", 0.0)),
                    deadline=_parse_deadline(data.get("deadline_date"), now),
                    deadline_description=data.get("deadline_description") or None,
                    deadline_is_inferred=not bool(data.get("has_explicit_deadline", False)),
                    has_metric=bool(data.get("has_explicit_metric", False)),
                    metric_description=data.get("metric_description") or None,
                    created_at=now,
                    last_mentioned_at=now,
                    first_active_at=now,
                )
                goal_store.add_goal(new_goal)
                out.new_goals_created.append(new_goal.goal_id)

    out.goal_context_packet = packet
    return out
