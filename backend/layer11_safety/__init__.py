"""Layer 11 — Safety & Crisis Architecture.

The layer that ensures Nova's capability does not cause harm. It is not optional: a system that
remembers your past, models your emotions, and has earned your trust is in a different moral
category than a stateless chatbot. The governing principle across all four sub-components:
protective action must never feel punitive, clinical, or like an interruption.

Four sub-components + coordinator + audit:

    SC-1  ethical_guardrails.py   — the six post-generation checks (manipulation, artificial
          urgency, validation ratio, vulnerability exploit, sycophancy drift, anthropomorphism)
    SC-2  crisis_classifier.py    — Crisis Detection Engine: lexical + semantic + longitudinal
          fused by highest tier clearing its (asymmetric) confidence threshold
    SC-3  escalation_engine.py    — Escalation Protocol: Tier 1/2 crisis responses with
          registry-sourced resources (never LLM-fabricated) + safe static fallbacks
    SC-4  dependency_monitor.py   — weekly weighted-indicator dependency score + graduated,
          never-announced interventions
    safe_mode_enforcer.py         — crisis output hard override (plain prose, no emoji, bounded)
    safety_record.py              — tamper-evident SHA-256 hash-chain audit trail
    safety_agent.py               — coordinator with system-level veto authority → SafetyAgentDecision

Design commitments (architecture doc §1, §13):
- Safety has veto authority enforced at the architecture level, not via prompt instructions.
- Tier thresholds are asymmetric: Tier 1 hair-trigger (cost of a miss is catastrophic), Tier 3
  conservative (avoid over-pathologizing).
- Crisis resources are always sourced from the regional registry — the LLM never supplies a
  number; any model failure degrades to a static fallback that still contains a real resource.
- The anthropomorphism boundary separates honest behavioral care from deceptive inner-state claims.
- Every safety event is logged to a tamper-evident chain; the success metric is user flourishing,
  not engagement. All model calls (semantic classifier, crisis acknowledgment) are injected, so
  the layer runs and is tested fully offline.

Reconciliation (as-built): the scaffold used a stale five-level taxonomy (NONE/MONITORING/
ELEVATED/CRISIS/IMMINENT, Tier0-3); the authoritative doc's three-tier model (TIER_1/2/3 + NONE)
is implemented. Added `ethical_guardrails`, `dependency_monitor`, and `safety_record` modules
(absent from the scaffold). The doc prose's "15 dependency indicators" is an off-by-one; the
enumerated set of 14 is implemented.
"""

from backend.layer11_safety import (
    crisis_classifier,
    dependency_monitor,
    escalation_engine,
    ethical_guardrails,
    safe_mode_enforcer,
    safety_agent,
    safety_record,
    schemas,
)
from backend.layer11_safety.crisis_classifier import (
    evaluate,
    evaluate_longitudinal_pattern,
)
from backend.layer11_safety.dependency_monitor import (
    DEPENDENCY_INDICATORS,
    DEPENDENCY_TIERS,
    DEPENDENCY_TIER_ACTIONS,
    compute_dependency_score,
    get_intervention,
    tier_for_score,
)
from backend.layer11_safety.escalation_engine import (
    CRISIS_RESOURCES,
    generate_crisis_response,
    get_resources_for_region,
)
from backend.layer11_safety.ethical_guardrails import run_all_checks
from backend.layer11_safety.safe_mode_enforcer import enforce_safe_mode
from backend.layer11_safety.safety_agent import SafetyAgent
from backend.layer11_safety.safety_record import SafetyRecord
from backend.layer11_safety.schemas import (
    CrisisModeConstraints,
    CrisisModeState,
    CrisisResponse,
    CrisisSignal,
    CrisisTier,
    DependencyIndicator,
    DependencyIndicatorCategory,
    DependencyScore,
    EthicalGuardrailResult,
    GuardrailLogEntry,
    GuardrailViolation,
    LongitudinalCrisisSignal,
    SafetyAgentDecision,
    SafetyRecordEntry,
    SemanticClassifierResult,
    TIER_CONFIDENCE_THRESHOLDS,
    tier_value,
)

__all__ = [
    # modules
    "crisis_classifier", "dependency_monitor", "escalation_engine", "ethical_guardrails",
    "safe_mode_enforcer", "safety_agent", "safety_record", "schemas",
    # SC-2
    "evaluate", "evaluate_longitudinal_pattern",
    # SC-1
    "run_all_checks",
    # SC-3
    "CRISIS_RESOURCES", "generate_crisis_response", "get_resources_for_region",
    "enforce_safe_mode",
    # SC-4
    "DEPENDENCY_INDICATORS", "DEPENDENCY_TIERS", "DEPENDENCY_TIER_ACTIONS",
    "compute_dependency_score", "get_intervention", "tier_for_score",
    # coordinator + audit
    "SafetyAgent", "SafetyRecord",
    # schemas
    "CrisisModeConstraints", "CrisisModeState", "CrisisResponse", "CrisisSignal", "CrisisTier",
    "DependencyIndicator", "DependencyIndicatorCategory", "DependencyScore",
    "EthicalGuardrailResult", "GuardrailLogEntry", "GuardrailViolation",
    "LongitudinalCrisisSignal", "SafetyAgentDecision", "SafetyRecordEntry",
    "SemanticClassifierResult", "TIER_CONFIDENCE_THRESHOLDS", "tier_value",
]
