"""Schemas for Layer 7 — Goals & Accountability Engine.

Layer 7 tracks meaningful, self-directed intentions the user mentions in conversation —
not a task manager, but the engine that holds the thread of a person's goals across
sessions and is genuinely invested in where they're going (architecture doc §1).

Five sub-components:

    SC-1 Goal Extractor                  (goal_extractor.py)
    SC-2 Goal Store                      (goal_store.py)
    SC-3 Progress Monitor                (progress_monitor.py)
    SC-4 Accountability Response Modifier (accountability_modifier.py)
    SC-5 Goal Decomposer                 (goal_decomposer.py)
    orchestrator                         (engine.py) → Layer7Output

Design commitments encoded here (architecture doc §11):
- Goals are inferred, never solicited.
- Progress is narrated, never scored to the user (scores are internal-only).
- Goals yield to the present moment (Layer 3 emotion, Layer 5 social) on conflict.
- Accountability is holding the thread, never pressure.
- Abandonment is valid data — archived with history, never re-surfaced unprompted.

Pure stdlib (dataclasses + str-Enum) so the layer runs and tests offline. The LLM calls
(SC-1 extraction, SC-3 deep inference, SC-5 decomposition) and embedding similarity are
injected as callables. The Layer 6 handoff reuses Layer 6's intake contract.

Split by sub-component into submodules; this ``__init__`` re-exports everything so
``from backend.layer7_goals.schemas import X`` keeps working unchanged.
"""

from __future__ import annotations

from .context import GoalContextPacket, GoalUWMUpdate, Layer7Output, RelevantGoal
from .enums import (
    GoalDirection,
    GoalDomain,
    GoalReferencePosition,
    GoalReferenceType,
    GoalSignalEventType,
    GoalSignalStrength,
    GoalStatus,
    HabitFrequency,
    MilestoneStatus,
    ProgressSignalType,
)
from .extraction import GoalExtractionResult
from .goal import Goal, GoalSignalEvent, Habit, Milestone
from .progress import GoalStateChange, ProgressSignalClassification

__all__ = [
    "Goal",
    "GoalContextPacket",
    "GoalDirection",
    "GoalDomain",
    "GoalExtractionResult",
    "GoalReferencePosition",
    "GoalReferenceType",
    "GoalSignalEvent",
    "GoalSignalEventType",
    "GoalSignalStrength",
    "GoalStateChange",
    "GoalStatus",
    "GoalUWMUpdate",
    "Habit",
    "HabitFrequency",
    "Layer7Output",
    "Milestone",
    "MilestoneStatus",
    "ProgressSignalClassification",
    "ProgressSignalType",
    "RelevantGoal",
]
