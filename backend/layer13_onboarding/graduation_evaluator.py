"""Layer 13 SC-2 — Graduation Evaluator (architecture doc §5.4).

Checked at the end of every session. Cold start ends only when ALL required criteria are met.
Graduation is *silent*: `execute_graduation()` produces no user-visible output — the conversation
simply continues while the full capability set (Layers 1–12) comes online behind the scenes.
Per §9, if evaluation/handoff fails the user stays in cold start and the system retries next
session (never a partial activation).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from .schemas import (
    GraduationCriterion,
    GraduationHandoff,
    GraduationResult,
    InitialState,
)

logger = logging.getLogger(__name__)


class GraduationEvaluator:
    REQUIRED_CRITERIA = [
        GraduationCriterion("minimum_sessions",
                            lambda s: s.cold_start_session_count >= 3,
                            "At least 3 sessions completed"),
        GraduationCriterion("minimum_exchanges",
                            lambda s: s.total_exchange_count >= 20,
                            "At least 20 message exchanges total"),
        GraduationCriterion("name_or_handle_known",
                            lambda s: s.user_handle is not None,
                            "User's name or handle is known"),
        GraduationCriterion("broad_life_context_known",
                            lambda s: s.life_phase is not None,
                            "Broad life context (student/working/etc.) is known"),
        GraduationCriterion("communication_style_established",
                            lambda s: s.communication_style_profile is not None,
                            "Communication style profile established from passive elicitation"),
        GraduationCriterion("emotional_baseline_calibrated",
                            lambda s: s.emotional_baseline_calibrated,
                            "Emotional baseline calibrated from observed sessions"),
        GraduationCriterion("primary_topic_areas_identified",
                            lambda s: len(s.primary_topic_areas) >= 2,
                            "At least 2 recurring topic areas identified"),
    ]

    NICE_TO_HAVE_CRITERIA = [
        GraduationCriterion("primary_reason_known",
                            lambda s: s.primary_reason is not None,
                            "Why user is using Nova — nice to have, not required"),
        GraduationCriterion("one_named_relationship",
                            lambda s: len(s.named_relationships) >= 1,
                            "At least one person mentioned by name"),
    ]

    def evaluate(self, state: InitialState) -> GraduationResult:
        met = [c for c in self.REQUIRED_CRITERIA if c.check(state)]
        failed = [c for c in self.REQUIRED_CRITERIA if not c.check(state)]
        nice_met = [c for c in self.NICE_TO_HAVE_CRITERIA if c.check(state)]
        return GraduationResult(
            should_graduate=len(failed) == 0,
            criteria_met=met,
            criteria_failed=failed,
            nice_to_have_met=nice_met,
        )

    def execute_graduation(self, state: InitialState, cold_start_engine) -> GraduationHandoff:
        """Silent handoff to normal runtime — no user-visible change."""
        cold_start_engine.deactivate_cold_start_config()
        cold_start_engine.set_personality_drift_gate(1.0)        # relax to full gate
        cold_start_engine.activate_proactivity_engine()
        cold_start_engine.activate_longitudinal_full_mode()
        cold_start_engine.trigger_first_chapter_creation(state)

        now = datetime.now(timezone.utc)
        state.cold_start = False
        state.cold_start_ends = now

        cold_start_engine.deactivate()                           # self-terminate

        logger.info("cold start graduated for user %s at session %d",
                    state.user_id, state.cold_start_session_count)
        return GraduationHandoff(
            graduated_at=now,
            session_count_at_graduation=state.cold_start_session_count,
            exchange_count_at_graduation=state.total_exchange_count,
            final_initial_state=state,
        )
