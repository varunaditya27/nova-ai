"""Schemas for Layer 13 — Onboarding & Cold Start Architecture (architecture doc §4-§7).

Pure-stdlib dataclasses + str-enums. Layer 13 is the temporary Cold Start Engine overlay:
Progressive Elicitation (SC-1), Cold Start Handling (SC-2), and Feature Introduction Pacing
(SC-3), coordinated by the ColdStartEngine, which self-terminates on graduation. Population
defaults here are the statistically-grounded starting points the doc specifies for unknown
users; `make_initial_state()` (context_constructor) is the factory because dataclasses with
mutable/nested defaults must not be shared across users.
"""

from __future__ import annotations

from backend.layer13_onboarding.schemas.coordinator import (
    MessageDirectives,
    SessionEndResult,
    SessionStartDirectives,
)
from backend.layer13_onboarding.schemas.cold_start_state import (
    ColdStartBehaviorConfig,
    CommunicationStyleProfile,
    EmotionalBaseline,
    InitialState,
    InitialStateUpdate,
    PersonalityVector,
    RelationshipStage,
)
from backend.layer13_onboarding.schemas.elicitation import ELICITATION_CATEGORIES, ElicitationItem
from backend.layer13_onboarding.schemas.feature_pacing import (
    FeatureIntroductionEvent,
    FeatureReadinessProfile,
    FeatureRelationalPrereqs,
    FeatureTechnicalPrereqs,
    IntroductionStyle,
)
from backend.layer13_onboarding.schemas.graduation import (
    GraduationCriterion,
    GraduationHandoff,
    GraduationResult,
)
from backend.layer13_onboarding.schemas.passive_signals import (
    CommunicationStyleUpdate,
    DisclosureComfort,
    EmotionalExpressionStyle,
    LifeContextSignals,
    NamedPersonSignal,
    PassiveSignalBundle,
    TopicApproach,
    UrgencySignal,
    VocabularyRegister,
)

__all__ = [
    # SC-1
    "ELICITATION_CATEGORIES", "ElicitationItem",
    "VocabularyRegister", "EmotionalExpressionStyle", "TopicApproach", "DisclosureComfort",
    "NamedPersonSignal", "LifeContextSignals", "UrgencySignal", "CommunicationStyleUpdate",
    "PassiveSignalBundle",
    # SC-2
    "PersonalityVector", "EmotionalBaseline", "CommunicationStyleProfile", "RelationshipStage",
    "InitialState", "InitialStateUpdate", "ColdStartBehaviorConfig",
    "GraduationCriterion", "GraduationResult", "GraduationHandoff",
    # SC-3
    "IntroductionStyle", "FeatureTechnicalPrereqs", "FeatureRelationalPrereqs",
    "FeatureReadinessProfile", "FeatureIntroductionEvent",
    # coordinator
    "SessionStartDirectives", "MessageDirectives", "SessionEndResult",
]
