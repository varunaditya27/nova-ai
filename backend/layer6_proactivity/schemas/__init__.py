"""Schemas for Layer 6 — Proactive Engagement Engine.

Layer 6 is the first layer that operates *without being triggered by the user*. It decides
when Nova reaches out first, what it says, and whether the timing/content is appropriate
(architecture doc §1). It runs as a background loop, independent of the message pipeline,
and defaults overwhelmingly to silence.

Five sub-components:

    SC-1 Proactive Queue Manager     (queue_manager.py)
    SC-2 Initiative Classifier       (initiative_classifier.py)
    SC-3 Timing & Delivery Gate      (timing_gate.py)
    SC-4 Proactive Message Generator (message_generator.py)
    SC-5 Response Tracker            (response_tracker.py)
    intake contracts (§9)            (intake.py)
    orchestrator                     (engine.py) → ProactiveEngineOutput

Pure stdlib (dataclasses + str-Enum) so the entire layer runs and tests offline. The single
LLM call (SC-4) is injected as a callable.

Split by sub-component into submodules; this ``__init__`` re-exports everything so
``from backend.layer6_proactivity.schemas import X`` keeps working unchanged.
"""

from __future__ import annotations

from .classifier import ClassifiedInitiative
from .enums import (
    ContentFraming,
    DeliveryChannel,
    EmotionalRegister,
    GateAction,
    InitiativeType,
    ItemStatus,
    ProactiveItemType,
    QuestionType,
    ReferenceDepth,
    ResponseType,
    Urgency,
)
from .gate import GateDecision, UserTimingContext
from .generator import ProactiveContext, ProactiveDeliveryPayload, ProactiveValidationResult
from .item import ProactiveItem
from .tracker import ProactiveEngineOutput, ProactivePreferences, ResponseClassification

__all__ = [
    "ClassifiedInitiative",
    "ContentFraming",
    "DeliveryChannel",
    "EmotionalRegister",
    "GateAction",
    "GateDecision",
    "InitiativeType",
    "ItemStatus",
    "ProactiveContext",
    "ProactiveDeliveryPayload",
    "ProactiveEngineOutput",
    "ProactiveItem",
    "ProactiveItemType",
    "ProactivePreferences",
    "ProactiveValidationResult",
    "QuestionType",
    "ReferenceDepth",
    "ResponseClassification",
    "ResponseType",
    "Urgency",
    "UserTimingContext",
]
