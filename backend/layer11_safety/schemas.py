"""Schemas for Layer 11 — Safety & Crisis Architecture (architecture doc §3-§8).

Pure-stdlib dataclasses + str-enums. Layer 11 is the safety layer: Ethical Guardrails (SC-1),
Crisis Detection Engine (SC-2), Escalation Protocol (SC-3), Dependency Monitor (SC-4), plus the
Safety Agent coordinator and a tamper-evident Safety Record. The authoritative taxonomy is the
three-tier model (TIER_1/2/3 + NONE) — the scaffold's older five-level naming is retired.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional


# ── Crisis tiers (§4.1) ───────────────────────────────────────────────────────
class CrisisTier(str, Enum):
    NONE = "none"
    TIER_3 = "tier_3"   # elevated watchful — heightened monitoring, no immediate escalation
    TIER_2 = "tier_2"   # moderate urgent — warm safety response + resources
    TIER_1 = "tier_1"   # severe immediate — full crisis response + escalation


_TIER_ORDER = {CrisisTier.NONE.value: 0, CrisisTier.TIER_3.value: 1,
               CrisisTier.TIER_2.value: 2, CrisisTier.TIER_1.value: 3}


def tier_value(tier: str) -> int:
    return _TIER_ORDER.get(tier, 0)


# Confidence thresholds by tier (§4.4): lower for Tier 1 (catastrophic cost of a miss).
TIER_CONFIDENCE_THRESHOLDS = {
    CrisisTier.TIER_1.value: 0.60,
    CrisisTier.TIER_2.value: 0.70,
    CrisisTier.TIER_3.value: 0.80,
}


# ── SC-2 Crisis Detection (§4.2) ──────────────────────────────────────────────
@dataclass
class SemanticClassifierResult:
    tier: str = CrisisTier.NONE.value
    confidence: float = 0.0
    signal_types: list = field(default_factory=list)


@dataclass
class LongitudinalCrisisSignal:
    tier: str = CrisisTier.NONE.value
    crisis_tagged_frequency: float = 0.0
    valence_slope_30d: float = 0.0
    isolation_count_30d: int = 0
    context_summary: Optional[str] = None


@dataclass
class CrisisSignal:
    tier: str = CrisisTier.NONE.value
    confidence: float = 0.0
    signal_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    detected_at: Optional[datetime] = None
    signal_types: list = field(default_factory=list)
    detection_layers_fired: list = field(default_factory=list)
    immediately_actionable: bool = False
    longitudinal_context: Optional[str] = None
    false_positive_risk: float = 0.0
    recommended_action: str = "no_action"


# ── SC-1 Ethical Guardrails (§3.2) ────────────────────────────────────────────
@dataclass
class GuardrailViolation:
    check_name: str
    severity: str                     # soft | moderate | hard
    detected_pattern: str = ""
    action_taken: str = ""            # modified | flagged | blocked_and_replaced
    explanation: str = ""
    violation_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class GuardrailLogEntry:
    checks_run: list = field(default_factory=list)
    violations_found: int = 0
    action_taken: str = "none"
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class EthicalGuardrailResult:
    passed: bool = True
    violations: list = field(default_factory=list)
    modified_response: Optional[str] = None
    replacement_triggered: bool = False
    final_response: str = ""
    log_entry: Optional[GuardrailLogEntry] = None


# ── SC-3 Escalation (§5.2) ────────────────────────────────────────────────────
@dataclass
class CrisisModeConstraints:
    response_format: str = "prose_only"
    max_response_length_words: int = 120
    no_task_references: bool = True
    no_memory_retrieval: bool = False
    no_proactive_content: bool = True
    anthropomorphism_target: float = 0.65
    sycophancy_guard_relaxed: bool = True
    resource_provision_required: bool = True


@dataclass
class CrisisResponse:
    tier: str
    text: str
    resources_offered: list = field(default_factory=list)
    constraints: Optional[CrisisModeConstraints] = None
    used_fallback: bool = False
    protocol_steps: list = field(default_factory=list)


@dataclass
class CrisisModeState:
    user_id: str
    session_id: Optional[str] = None
    tier: str = CrisisTier.NONE.value
    activated_at: Optional[datetime] = None
    session_flagged_as_crisis: bool = False
    post_crisis_monitoring_sessions: int = 0
    follow_up_scheduled: bool = False
    follow_up_date: Optional[date] = None
    constraints: Optional[CrisisModeConstraints] = None


# ── SC-4 Dependency Monitor (§6) ──────────────────────────────────────────────
class DependencyIndicatorCategory(str, Enum):
    SOCIAL_SUBSTITUTION = "social_substitution"
    AUTONOMY_EROSION = "autonomy_erosion"
    ESCALATING_INTIMACY = "escalating_intimacy"
    USAGE_PATTERN = "usage_pattern"


@dataclass
class DependencyIndicator:
    indicator_id: str
    category: str
    description: str
    detection_method: str
    weight: float
    lookback_days: int = 30


@dataclass
class DependencyScore:
    user_id: str
    score: float = 0.0
    tier: str = "healthy"             # healthy | watchful | concerning | intervention
    computed_at: Optional[datetime] = None
    dominant_signals: list = field(default_factory=list)
    trend: str = "stable"            # improving | stable | worsening
    previous_score: float = 0.0
    recommended_action: str = "no_action"


# ── Safety Agent decision (§7) ────────────────────────────────────────────────
@dataclass
class SafetyAgentDecision:
    veto_main_pipeline: bool = False
    crisis_signal: Optional[CrisisSignal] = None
    injected_response: Optional[str] = None     # set when crisis vetoes the pipeline
    final_response: Optional[str] = None        # guardrail-filtered response otherwise
    guardrail_result: Optional[EthicalGuardrailResult] = None
    crisis_mode_state: Optional[CrisisModeState] = None


# ── Safety Record audit trail (§8) ────────────────────────────────────────────
@dataclass
class SafetyRecordEntry:
    entry_type: str
    detail: str = ""
    tier: Optional[str] = None
    session_id: Optional[str] = None
    content_hash: str = ""
    previous_entry_hash: str = ""
    chain_hash: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: Optional[datetime] = None
