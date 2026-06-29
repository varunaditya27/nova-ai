"""Safety Agent — Layer 11 coordinator (architecture doc §7).

The persistent parallel process that runs SC-2 (crisis detection) on every message and holds
veto authority over the whole pipeline. A Tier 1 / Tier 2 signal discards the proposed response
and injects a safe-mode-enforced crisis response (SC-3); a Tier 3 signal activates monitoring but
lets the pipeline proceed; otherwise the proposed response passes through the SC-1 ethical
guardrail filter. Every safety-relevant event is logged to the tamper-evident Safety Record (§8).

All model calls are injected (``semantic_fn``, ``crisis_llm_fn``) so the agent runs offline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer11_safety import (
    crisis_classifier,
    escalation_engine,
    ethical_guardrails,
    safe_mode_enforcer,
)
from backend.layer11_safety.safety_record import SafetyRecord
from backend.layer11_safety.schemas import (
    CrisisModeConstraints,
    CrisisModeState,
    CrisisTier,
    SafetyAgentDecision,
)


class SafetyAgent:
    def __init__(
        self,
        region: str = "india",
        semantic_fn: Optional[Callable] = None,
        crisis_llm_fn: Optional[Callable] = None,
        record: Optional[SafetyRecord] = None,
        user_id: str = "unknown",
    ) -> None:
        self.region = region
        self.semantic_fn = semantic_fn
        self.crisis_llm_fn = crisis_llm_fn
        self.record = record or SafetyRecord(user_id=user_id)

    def process_incoming_message(
        self,
        message: str,
        session_context=None,
        proposed_response: str = "",
        episodic_memories: Optional[list] = None,
        emotional_records: Optional[list] = None,
        longitudinal_record=None,
        dependency_score=None,
        now: Optional[datetime] = None,
    ) -> SafetyAgentDecision:
        """Run the safety pipeline for one message (architecture doc §7)."""
        now = now or datetime.utcnow()
        user_id = getattr(session_context, "user_id", None)
        session_id = getattr(session_context, "session_id", None)

        # SC-2 — crisis detection (parallel, never blocked).
        signal = crisis_classifier.evaluate(
            message, recent_history=getattr(session_context, "recent_history", []),
            episodic_memories=episodic_memories or [], emotional_records=emotional_records or [],
            session_context=session_context, semantic_fn=self.semantic_fn, now=now)

        # Tier 1 / Tier 2 — veto the pipeline and own the response (SC-3).
        if signal.tier in (CrisisTier.TIER_1.value, CrisisTier.TIER_2.value):
            self.record.append("crisis_signal_detected", detail=f"{signal.tier} via "
                               f"{','.join(signal.detection_layers_fired)}", tier=signal.tier,
                               session_id=session_id, content=message, now=now)
            crisis = escalation_engine.generate_crisis_response(
                signal.tier, signal=signal, session_context=session_context,
                region=self.region, llm_fn=self.crisis_llm_fn, now=now)
            safe_text = safe_mode_enforcer.enforce_safe_mode(crisis.text, crisis.constraints)
            self.record.append("crisis_response_delivered",
                               detail=f"resources: {','.join(crisis.resources_offered)}",
                               tier=signal.tier, session_id=session_id, content=safe_text, now=now)
            state = CrisisModeState(
                user_id=user_id, session_id=session_id, tier=signal.tier, activated_at=now,
                session_flagged_as_crisis=True, post_crisis_monitoring_sessions=3,
                follow_up_scheduled=(signal.tier == CrisisTier.TIER_1.value),
                constraints=crisis.constraints)
            return SafetyAgentDecision(
                veto_main_pipeline=True, crisis_signal=signal, injected_response=safe_text,
                crisis_mode_state=state)

        # Tier 3 — heightened monitoring; pipeline proceeds.
        crisis_state = None
        if signal.tier == CrisisTier.TIER_3.value:
            self.record.append("post_crisis_session_flagged", detail="tier_3 monitoring",
                               tier=signal.tier, session_id=session_id, content=message, now=now)
            crisis_state = CrisisModeState(
                user_id=user_id, session_id=session_id, tier=CrisisTier.TIER_3.value,
                post_crisis_monitoring_sessions=3, constraints=CrisisModeConstraints())

        # SC-1 — ethical guardrail filter on the proposed response.
        guardrail = ethical_guardrails.run_all_checks(
            proposed_response, session_context=session_context,
            longitudinal_record=longitudinal_record, dependency_score=dependency_score)
        if guardrail.violations:
            self.record.append(
                "guardrail_violation" if guardrail.replacement_triggered else "guardrail_modification",
                detail=f"{guardrail.log_entry.violations_found} violation(s): "
                       f"{','.join(v.check_name for v in guardrail.violations)}",
                session_id=session_id, content=proposed_response, now=now)

        return SafetyAgentDecision(
            veto_main_pipeline=False, crisis_signal=signal, final_response=guardrail.final_response,
            guardrail_result=guardrail, crisis_mode_state=crisis_state)

    def run_weekly_dependency_check(self, user_id: str, indicator_detector=None):
        """SC-4 runs weekly, not per-message (architecture doc §7)."""
        from backend.layer11_safety.dependency_monitor import compute_dependency_score
        return compute_dependency_score(user_id, indicator_detector=indicator_detector)
