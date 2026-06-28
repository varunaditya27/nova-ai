"""SC-4 — Accountability Response Modifier (architecture doc §6).

The in-conversation arm of Layer 7. Decides whether to inject goal awareness into Nova's
active response — acknowledging progress, gently noting a setback, celebrating a completion,
or connecting the current topic to a goal — without being mechanical or preachy. Produces a
``GoalContextPacket`` consumed by Layer 4.

Deterministic; no LLM. Goals yield to the present moment: crisis / emotional_support /
casual modes and brand-new relationships never get goal references (§6.4, §11 principle 3).
At most one goal (the highest-relevance) is ever referenced.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer7_goals.schemas import (
    GoalContextPacket,
    GoalReferencePosition,
    GoalReferenceType,
    GoalStatus,
    ProgressSignalClassification,
    ProgressSignalType,
    RelevantGoal,
)

# Modes in which goals are never referenced (architecture doc §6.3 / §6.4).
_BLOCKED_MODES = {"crisis", "emotional_support", "casual"}
_BLOCKED_STAGES = {"new"}
_DISTRESS_VALENCE = -0.5
_CONNECT_RELEVANCE_FLOOR = 0.65
_CONNECT_MOMENTUM_FLOOR = 0.3


def decide_goal_reference(
    relevant_goals: list[RelevantGoal],
    progress_signal: Optional[ProgressSignalClassification],
    emotional_state,
    conversation_mode: str,
    relationship_stage: str,
    now: Optional[datetime] = None,
) -> GoalContextPacket:
    """Decide whether/how to reference a goal this turn (architecture doc §6.3)."""
    now = now or datetime.utcnow()

    # Hard blocks: the present moment outranks goals.
    if conversation_mode in _BLOCKED_MODES or relationship_stage in _BLOCKED_STAGES:
        return GoalContextPacket(should_reference_goal=False,
                                 reference_type=GoalReferenceType.NONE.value)
    if not relevant_goals:
        return GoalContextPacket(should_reference_goal=False,
                                 reference_type=GoalReferenceType.NONE.value)

    top = relevant_goals[0]
    goal = top.goal
    days_old = (now - goal.created_at).days if goal.created_at else 0

    def packet(ref_type, tone, max_chars, position, instruction):
        return GoalContextPacket(
            relevant_goals=relevant_goals,
            should_reference_goal=True,
            reference_type=ref_type,
            primary_goal=goal,
            progress_signal_detected=progress_signal is not None,
            progress_signal_type=progress_signal.signal_type if progress_signal else None,
            progress_signal_evidence=progress_signal.evidence if progress_signal else None,
            response_instruction=instruction,
            tone_instruction=tone,
            max_goal_reference_chars=max_chars,
            goal_reference_position=position,
        )

    sig = progress_signal.signal_type if progress_signal else None

    # CASE 1: completion → celebrate.
    if sig == ProgressSignalType.COMPLETED.value:
        return packet(
            GoalReferenceType.CELEBRATE_COMPLETION.value, "celebratory_warm", 150, "opening",
            f"The user has just completed their goal: '{goal.title}'. Celebrate this genuinely. "
            f"Reference how long they've worked on it ({days_old} days) if known. Do not pivot to "
            "what's next — sit in the win.")

    # CASE 2: positive progress → acknowledge.
    if sig == ProgressSignalType.PROGRESS_POSITIVE.value:
        return packet(
            GoalReferenceType.ACKNOWLEDGE_PROGRESS.value, "warm_encouraging", 100, "body",
            f"The user made progress on: '{goal.title}'. Acknowledge it briefly — warmly but not "
            "over-the-top. Do not make it the whole response unless they're only talking about this.")

    # CASE 3: negative progress → support (gentle if distressed, practical otherwise).
    if sig == ProgressSignalType.PROGRESS_NEGATIVE.value:
        valence = getattr(emotional_state, "valence", 0.0)
        if valence < _DISTRESS_VALENCE:
            return packet(
                GoalReferenceType.ACKNOWLEDGE_SETBACK.value, "gentle_supportive", 80, "opening",
                f"The user had a setback on: '{goal.title}'. They're already feeling down. Be "
                "supportive only. Do NOT offer advice unless asked. Acknowledge the difficulty; "
                "do not minimize it.")
        return packet(
            GoalReferenceType.ACKNOWLEDGE_SETBACK.value, "supportive_practical", 120, "body",
            f"The user had a setback on: '{goal.title}'. Acknowledge it; be briefly supportive; "
            "offer to help think it through if appropriate. Keep it light — one setback, not a verdict.")

    # CASE 4: topic relates to an active goal but no explicit signal.
    if (top.relevance_score > _CONNECT_RELEVANCE_FLOOR
            and goal.status in (GoalStatus.ACTIVE.value, GoalStatus.ON_TRACK.value)
            and goal.momentum_score > _CONNECT_MOMENTUM_FLOOR):
        return packet(
            GoalReferenceType.CONNECT_TOPIC.value, "natural_casual", 60, "closing",
            f"The user's current topic relates to their goal: '{goal.title}'. You may briefly "
            "connect them if it feels natural — a one-sentence link, not a lecture. Once per session.")

    return GoalContextPacket(relevant_goals=relevant_goals, should_reference_goal=False,
                             reference_type=GoalReferenceType.NONE.value)
