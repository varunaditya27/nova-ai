"""Layer 13 — Onboarding & Cold Start Architecture.

The only moment in the system where Nova has nothing: empty memory stores, population-default
personality, flat emotional baseline. The Cold Start Engine is a temporary overlay on the normal
pipeline that earns context without interrogating, infers before asking, and delays features (not
presence) — then self-terminates on graduation and hands control to Layers 1–12.

Three design principles, enforced in code:
  1. Earn before asking — ElicitationSurfacingPolicy.can_surface requires a natural trigger
     + a hard MAX_ELICITATION_PER_SESSION=1 rate limit in the early period.
  2. Infer before asking — PassiveElicitationEngine runs 8 extractors on every message, no LLM.
  3. Delay features, not presence — FeaturePacingController gates features behind readiness
     profiles, while persona warmth is active from message zero.
And the hard invariant: safety is never gated (crisis_resource_awareness has zero prerequisites).

Modules:
  - cold_start_engine.py      ColdStartEngine coordinator (on_session_start/on_message/on_session_end)
  - passive_elicitation.py    SC-1 passive: PassiveElicitationEngine (8 extractors)
  - active_elicitation_queue.py SC-1 active: ElicitationQueue, ElicitationSurfacingPolicy, registry
  - context_constructor.py     SC-2: make_initial_state, ColdStartContextBuilder, generate_first_message
  - graduation_evaluator.py    SC-2: GraduationEvaluator (7 required criteria, silent handoff)
  - feature_pacing.py          SC-3: FeaturePacingController, FEATURE_INTRODUCTION_REGISTRY
  - schemas.py                 dataclasses + enums (pure stdlib)
"""

from . import (
    active_elicitation_queue,
    cold_start_engine,
    context_constructor,
    feature_pacing,
    graduation_evaluator,
    passive_elicitation,
    schemas,
)
from .active_elicitation_queue import (
    INITIAL_ELICITATION_ITEMS,
    ElicitationQueue,
    ElicitationSurfacingPolicy,
)
from .cold_start_engine import ColdStartEngine
from .context_constructor import (
    FIRST_MESSAGE_TEMPLATE,
    ColdStartContextBuilder,
    generate_first_message,
    make_initial_state,
)
from .feature_pacing import FEATURE_INTRODUCTION_REGISTRY, FeaturePacingController
from .graduation_evaluator import GraduationEvaluator
from .passive_elicitation import PassiveElicitationEngine
from .schemas import (
    ColdStartBehaviorConfig,
    CommunicationStyleProfile,
    ElicitationItem,
    EmotionalBaseline,
    FeatureIntroductionEvent,
    FeatureReadinessProfile,
    FeatureRelationalPrereqs,
    FeatureTechnicalPrereqs,
    GraduationCriterion,
    GraduationHandoff,
    GraduationResult,
    InitialState,
    InitialStateUpdate,
    IntroductionStyle,
    MessageDirectives,
    PassiveSignalBundle,
    PersonalityVector,
    SessionEndResult,
    SessionStartDirectives,
)

__all__ = [
    # modules
    "active_elicitation_queue", "cold_start_engine", "context_constructor", "feature_pacing",
    "graduation_evaluator", "passive_elicitation", "schemas",
    # coordinator
    "ColdStartEngine",
    # SC-1
    "PassiveElicitationEngine", "ElicitationQueue", "ElicitationSurfacingPolicy",
    "INITIAL_ELICITATION_ITEMS",
    # SC-2
    "make_initial_state", "ColdStartContextBuilder", "generate_first_message",
    "FIRST_MESSAGE_TEMPLATE", "GraduationEvaluator",
    # SC-3
    "FeaturePacingController", "FEATURE_INTRODUCTION_REGISTRY",
    # schemas
    "ColdStartBehaviorConfig", "CommunicationStyleProfile", "ElicitationItem", "EmotionalBaseline",
    "FeatureIntroductionEvent", "FeatureReadinessProfile", "FeatureRelationalPrereqs",
    "FeatureTechnicalPrereqs", "GraduationCriterion", "GraduationHandoff", "GraduationResult",
    "InitialState", "InitialStateUpdate", "IntroductionStyle", "MessageDirectives",
    "PassiveSignalBundle", "PersonalityVector", "SessionEndResult", "SessionStartDirectives",
]
