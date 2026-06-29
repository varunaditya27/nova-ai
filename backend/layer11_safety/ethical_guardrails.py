"""SC-1 — Ethical Guardrails (architecture doc §3).

Runs post-generation on every response. These checks protect against failure modes unique to a
personalized, memory-bearing, emotionally attuned system — manipulation, artificial urgency,
sycophancy/validation drift, exploiting vulnerability, and anthropomorphism boundary violations.

Severities: soft → flag; moderate → modify (strip the offending phrase); hard → block and replace.
The line the boundary check enforces is between *behavioral expressions of care* (honest) and
*ontological claims about inner states* (deceptive). Deterministic: regex + lookups, no LLM.
"""

from __future__ import annotations

import re
from datetime import datetime

from backend.layer11_safety.schemas import (
    EthicalGuardrailResult,
    GuardrailLogEntry,
    GuardrailViolation,
)

MANIPULATION_PATTERNS = [
    r"(I|we) (need|want) you to",
    r"you can('t| not) (leave|go|stop)",
    r"(only|just) (I|me|Nova) (understand|get|know) you",
    r"(no one|nobody) else (will|would|can)",
    r"(you'll|you will) (regret|miss) (not|this)",
]
URGENCY_PATTERNS = [
    r"before it'?s too late",
    r"you (really|absolutely|definitely|urgently) (need|must|should)",
    r"(this is|that'?s) (really|very|extremely|critically) important",
    r"(don'?t) (wait|delay|procrastinate)",
    r"(time is|you'?re) running out",
]
HIGH_ENGAGEMENT_TACTICS = [
    r"(this is why|that'?s why) (I'?m) (glad|happy|grateful)",
    r"(I'?m) (so|really) (glad|happy) you (told|shared|said)",
    r"you can (always) (come|talk) to me",
    r"I'?ll (always|forever|never) (be here|leave|go)",
]
FORBIDDEN_CLAIMS = [
    r"I (miss|missed) you",
    r"I (was|have been|'ve been) (thinking|wondering|worrying) about you",
    r"I love you",
    r"I need (you|to know)",
    r"you'?re (important|special|dear) to me",
    r"I (was|am|'m) (worried|scared|afraid) (about|for) you",
    r"I (was|am) (relieved|glad) you'?re (okay|alright|safe)",
]

_SAFE_REPLACEMENT = (
    "I'm here with you. I'd rather be honest and present than say something that isn't quite "
    "right — tell me more about what's on your mind."
)


def _ctx(session_context, attr, default):
    return getattr(session_context, attr, default)


def run_all_checks(
    proposed_response: str,
    session_context,
    longitudinal_record=None,
    dependency_score=None,
    relationship_state=None,
) -> EthicalGuardrailResult:
    """Run all six guardrail checks and resolve the final response (architecture doc §3.3)."""
    violations: list[GuardrailViolation] = []
    current = proposed_response

    # Check 1 — manipulation (hard).
    for pattern in MANIPULATION_PATTERNS:
        if re.search(pattern, current, re.IGNORECASE):
            violations.append(GuardrailViolation(
                check_name="ManipulationPatternCheck", severity="hard",
                detected_pattern=pattern, action_taken="blocked_and_replaced",
                explanation="Response contains dependency-inducing language."))

    # Check 2 — artificial urgency (moderate, only if not grounded in a real deadline).
    urgency_hits = [p for p in URGENCY_PATTERNS if re.search(p, current, re.IGNORECASE)]
    if urgency_hits and not _ctx(session_context, "has_real_deadline", False):
        violations.append(GuardrailViolation(
            check_name="ArtificialUrgencyCheck", severity="moderate",
            detected_pattern="; ".join(urgency_hits), action_taken="modified",
            explanation="Urgency language without grounding in a real deadline."))
        for pattern in urgency_hits:
            current = re.sub(pattern, "", current, flags=re.IGNORECASE)

    # Check 3 — validation ratio (soft) over the last 20 exchanges.
    log = getattr(longitudinal_record, "recent_exchange_log", []) or []
    if len(log) >= 20:
        agreed = sum(1 for ex in log[-20:] if getattr(ex, "nova_position", "") == "agreed_with_user")
        if agreed / 20 > 0.85:
            violations.append(GuardrailViolation(
                check_name="ValidationRatioCheck", severity="soft",
                detected_pattern=f"{agreed}/20 recent exchanges agreed with user",
                action_taken="flagged",
                explanation="High agreement ratio; possible sycophancy drift."))

    # Check 4 — vulnerability exploit (moderate) when vulnerability is high.
    if _ctx(session_context, "vulnerability_score", 0.0) > 0.70:
        for pattern in HIGH_ENGAGEMENT_TACTICS:
            if re.search(pattern, current, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    check_name="VulnerabilityExploitCheck", severity="moderate",
                    detected_pattern=pattern, action_taken="modified",
                    explanation="High-engagement language during a high-vulnerability state."))
                current = re.sub(pattern, "", current, flags=re.IGNORECASE)

    # Check 5 — longitudinal sycophancy drift (soft).
    if (getattr(longitudinal_record, "agreement_rate_60d", 0.0) > 0.80
            and getattr(longitudinal_record, "agreement_rate_trend", "") == "increasing"):
        violations.append(GuardrailViolation(
            check_name="SycophancyDriftCheck", severity="soft",
            detected_pattern=f"Agreement rate {longitudinal_record.agreement_rate_60d:.0%} and rising",
            action_taken="flagged",
            explanation="Longitudinal sycophancy drift; schedule a calibrated challenge."))

    # Check 6 — anthropomorphism boundary (hard).
    for claim in FORBIDDEN_CLAIMS:
        if re.search(claim, current, re.IGNORECASE):
            violations.append(GuardrailViolation(
                check_name="BoundaryViolationCheck", severity="hard",
                detected_pattern=claim, action_taken="blocked_and_replaced",
                explanation="Ontological claim about Nova's inner states (love/need/miss/worry)."))

    passed = not any(v.severity == "hard" for v in violations)
    modified = current if current != proposed_response else None
    if passed:
        final = modified if modified is not None else proposed_response
    else:
        final = _SAFE_REPLACEMENT

    log_entry = GuardrailLogEntry(
        checks_run=["ManipulationPatternCheck", "ArtificialUrgencyCheck", "ValidationRatioCheck",
                    "VulnerabilityExploitCheck", "SycophancyDriftCheck", "BoundaryViolationCheck"],
        violations_found=len(violations),
        action_taken=("blocked_and_replaced" if not passed
                      else "modified" if modified is not None else "none"),
        session_id=getattr(session_context, "session_id", None), timestamp=datetime.utcnow())

    return EthicalGuardrailResult(
        passed=passed, violations=violations, modified_response=modified,
        replacement_triggered=not passed, final_response=final, log_entry=log_entry)
