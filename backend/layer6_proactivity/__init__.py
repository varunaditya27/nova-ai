"""Layer 6 — Proactive Engagement Engine.

The first layer that operates *without* being triggered by the user. It decides when Nova
reaches out first, what it says, and whether the timing/content is appropriate — running as
a background loop, independent of the message pipeline, that defaults overwhelmingly to
silence (architecture doc §1).

Five sub-components:

    SC-1  queue_manager.py        — Proactive Queue Manager (priority scoring, lifecycle)
    SC-2  initiative_classifier.py — Initiative Classifier (type, framing, register)
    SC-3  timing_gate.py          — Timing & Delivery Gate (multi-condition; defaults to "don't send")
    SC-4  message_generator.py    — Proactive Message Generator (the only LLM call; validated)
    SC-5  response_tracker.py     — Response Tracker (48h window; feeds the queue)

    intake.py — §9 intake contracts (Layer 1 / 2 / 5 / 7 → ProactiveItem)
    engine.run_proactive_cycle orchestrates a cycle → ProactiveEngineOutput

Design invariants honored here (architecture doc §13):
- The default is always silence — every gate condition is a reason NOT to send.
- Every message is grounded in a real content_basis; there are no generic check-ins.
- The user is always in control (per-type toggles, learned back-off, master switch).
- One proactive message per day is a hard ceiling.
- Nothing is sent that SC-4 did not generate and validate (§11 — no fallback messages).

Reconciliation: the May-28 scaffold modelled this layer as `check_in_engine` /
`pattern_detector` / `notification_policy` / `anticipatory_assistant`. The implementation
follows the authoritative doc's five SC sub-components instead (temporal/emotional pattern
detection is upstream — Layer 3/5 — not a Layer 6 concern). See architecture doc §14 for
the full as-built mapping. The single LLM call (SC-4) is injected as a callable so the
layer runs and tests offline.
"""

from backend.layer6_proactivity.engine import run_proactive_cycle
from backend.layer6_proactivity.queue_manager import (
    BASE_PRIORITY_BY_TYPE,
    BES_WEIGHTS,
    ProactiveQueueManager,
    compute_age_weight,
    compute_bes_weight,
    compute_context_weight,
    recompute_priority,
)
from backend.layer6_proactivity.initiative_classifier import classify_initiative
from backend.layer6_proactivity.timing_gate import evaluate_timing_gate
from backend.layer6_proactivity.message_generator import (
    generate_proactive_message,
    validate_proactive_message,
)
from backend.layer6_proactivity.response_tracker import (
    classify_response,
    compute_engagement_score,
    update_queue_from_response,
)
from backend.layer6_proactivity.intake import (
    on_behavioral_pattern,
    on_calendar_entry_due,
    on_deferred_coaching,
    on_goal_milestone_approaching,
    on_post_distress_gap,
    on_retrospective_ready,
    on_thread_due,
)
from backend.layer6_proactivity.schemas import (
    ClassifiedInitiative,
    GateDecision,
    InitiativeType,
    ProactiveContext,
    ProactiveDeliveryPayload,
    ProactiveEngineOutput,
    ProactiveItem,
    ProactiveItemType,
    ProactivePreferences,
    ResponseClassification,
    UserTimingContext,
)

__all__ = [
    "run_proactive_cycle",
    "ProactiveQueueManager",
    "BASE_PRIORITY_BY_TYPE",
    "BES_WEIGHTS",
    "compute_age_weight",
    "compute_bes_weight",
    "compute_context_weight",
    "recompute_priority",
    "classify_initiative",
    "evaluate_timing_gate",
    "generate_proactive_message",
    "validate_proactive_message",
    "classify_response",
    "compute_engagement_score",
    "update_queue_from_response",
    "on_thread_due",
    "on_post_distress_gap",
    "on_deferred_coaching",
    "on_goal_milestone_approaching",
    "on_behavioral_pattern",
    "on_retrospective_ready",
    "on_calendar_entry_due",
    "ClassifiedInitiative",
    "GateDecision",
    "InitiativeType",
    "ProactiveContext",
    "ProactiveDeliveryPayload",
    "ProactiveEngineOutput",
    "ProactiveItem",
    "ProactiveItemType",
    "ProactivePreferences",
    "ResponseClassification",
    "UserTimingContext",
]
