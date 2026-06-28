"""Layer 7 — Goals & Accountability Engine.

Tracks meaningful, self-directed intentions the user mentions in conversation — not a task
manager, but the engine that holds the thread of a person's goals across sessions and is
genuinely invested in where they're going (architecture doc §1).

Five sub-components:

    SC-1  goal_extractor.py          — Goal Extractor (pre-filter + LLM extraction + dedup)
    SC-2  goal_store.py              — Goal Store (lifecycle transitions + relevance retrieval)
    SC-3  progress_monitor.py        — Progress Monitor (signal classification, momentum, staleness)
    SC-4  accountability_modifier.py — Accountability Response Modifier → GoalContextPacket
    SC-5  goal_decomposer.py         — Goal Decomposer (milestones/habits + Layer 6 handoff)

    engine.run_goal_pipeline orchestrates the per-message path → Layer7Output

Design commitments honored here (architecture doc §11):
- Goals are inferred, never solicited (no goal-entry UI; the extractor listens).
- Progress is narrated, never scored to the user (scores are internal-only ranking signals).
- Goals yield to the present moment — crisis/emotional_support/casual suppress references.
- Accountability is holding the thread, never pressure or shaming setbacks.
- Abandonment is valid data — archived with history, never re-surfaced unprompted.
- A failure in any component never blocks response generation (§10).

Reconciliation: the May-28 scaffold modelled this layer with `goal_lifecycle` / `task_engine`
/ `conflict_detector` / `life_event_tracker`. The implementation follows the authoritative
doc's five SC sub-components instead: lifecycle is folded into `goal_store`; task plans,
goal-conflict detection, and life-event cascades are out of scope for the Layer 7 spec. See
architecture doc §13 for the full as-built mapping. The three LLM uses (extraction, deep
inference, decomposition) and embedding similarity are injected as callables so the layer
runs offline; the Layer 6 milestone handoff reuses Layer 6's intake contract.
"""

from backend.layer7_goals.engine import run_goal_pipeline
from backend.layer7_goals.goal_extractor import (
    GOAL_SIGNAL_KEYWORDS,
    extract_goal,
    is_duplicate_goal,
    should_run_extractor,
)
from backend.layer7_goals.goal_store import (
    STATUS_TRANSITIONS,
    GoalStore,
    apply_transition,
)
from backend.layer7_goals.progress_monitor import (
    classify_progress_signal,
    compute_momentum,
    run_staleness_scan,
    update_progress_score,
)
from backend.layer7_goals.accountability_modifier import decide_goal_reference
from backend.layer7_goals.goal_decomposer import (
    check_milestone_completion,
    decompose_goal,
    register_milestones_with_layer6,
)
from backend.layer7_goals.schemas import (
    Goal,
    GoalContextPacket,
    GoalDirection,
    GoalDomain,
    GoalExtractionResult,
    GoalStateChange,
    GoalStatus,
    Habit,
    Layer7Output,
    Milestone,
    ProgressSignalClassification,
    RelevantGoal,
)

__all__ = [
    "run_goal_pipeline",
    "should_run_extractor",
    "is_duplicate_goal",
    "extract_goal",
    "GOAL_SIGNAL_KEYWORDS",
    "GoalStore",
    "apply_transition",
    "STATUS_TRANSITIONS",
    "classify_progress_signal",
    "update_progress_score",
    "compute_momentum",
    "run_staleness_scan",
    "decide_goal_reference",
    "decompose_goal",
    "register_milestones_with_layer6",
    "check_milestone_completion",
    "Goal",
    "GoalContextPacket",
    "GoalDirection",
    "GoalDomain",
    "GoalExtractionResult",
    "GoalStateChange",
    "GoalStatus",
    "Habit",
    "Layer7Output",
    "Milestone",
    "ProgressSignalClassification",
    "RelevantGoal",
]
