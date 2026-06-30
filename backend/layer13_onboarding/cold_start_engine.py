"""Layer 13 — Cold Start Engine coordinator (architecture doc §7).

Temporary overlay on the normal conversation pipeline, active from new-user creation until
graduation. Coordinates SC-1 (passive engine + active queue + surfacing policy), SC-2 (context
builder + graduation evaluator) and SC-3 (feature pacing controller), then self-terminates and
hands full control to the Conversation Orchestrator. Safety (Layer 11) is never gated by this
overlay; the `personality_drift_gate`/`set_*`/`activate_*` callbacks model the graduation handoff
into the live system (wired by the orchestrator in production).
"""

from __future__ import annotations

import copy
import logging

from .active_elicitation_queue import (
    INITIAL_ELICITATION_ITEMS,
    ElicitationQueue,
    ElicitationSurfacingPolicy,
)
from .context_constructor import ColdStartContextBuilder, make_initial_state
from .feature_pacing import FeaturePacingController
from .graduation_evaluator import GraduationEvaluator
from .passive_elicitation import PassiveElicitationEngine
from .schemas import (
    ColdStartBehaviorConfig,
    MessageDirectives,
    SessionEndResult,
    SessionStartDirectives,
)

logger = logging.getLogger(__name__)


class ColdStartEngine:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = make_initial_state(user_id)
        self.config = ColdStartBehaviorConfig()
        self.active = True
        self._drift_gate = self.config.personality_drift_gate_multiplier

        self.passive_elicitation_engine = PassiveElicitationEngine()
        self.active_elicitation_queue = ElicitationQueue(
            user_id=user_id, items=copy.deepcopy(INITIAL_ELICITATION_ITEMS))
        self.elicitation_surfacing_policy = ElicitationSurfacingPolicy()
        self.context_builder = ColdStartContextBuilder(self.passive_elicitation_engine)
        self.graduation_evaluator = GraduationEvaluator()
        self.feature_pacing_controller = FeaturePacingController()

    # ── lifecycle ────────────────────────────────────────────────────────────
    def on_session_start(self, session_context) -> SessionStartDirectives:
        self.state.cold_start_session_count += 1
        return SessionStartDirectives(
            cold_start_active=True,
            personality_drift_gate=self.config.personality_drift_gate_multiplier,
            proactivity_mode=self.config.proactivity_mode,
            longitudinal_mode=self.config.longitudinal_mode,
            max_elicitation_this_session=self.config.max_elicitation_per_session,
            active_features=self.feature_pacing_controller.get_all_active_features(
                state=self.state, session_context=session_context),
        )

    def on_message(self, message: str, session_context, timestamp) -> MessageDirectives:
        self.state.total_exchange_count += 1

        # 1-2. passive extraction → InitialState update
        state_update = self.context_builder.process_message(
            message=message, message_index=self.state.total_exchange_count - 1,
            session_number=self.state.cold_start_session_count, timestamp=timestamp,
            initial_state=self.state, session_history=session_context.recent_history)
        self.state.apply_update(state_update)

        # 3. active elicitation: at most one question, only when all conditions hold
        surfaceable = self.active_elicitation_queue.next_surfaceable_item(
            session_context=session_context,
            current_session_number=self.state.cold_start_session_count,
            emotional_intensity=session_context.emotional_intensity,
            topic_in_progress=session_context.current_topic)
        pending = None
        if surfaceable and self.elicitation_surfacing_policy.can_surface(
                item=surfaceable, session_context=session_context,
                current_session_number=self.state.cold_start_session_count,
                emotional_intensity=session_context.emotional_intensity,
                elicitation_count_this_session=session_context.elicitation_count_this_session):
            surfaceable.status = "surfaced"
            surfaceable.surfaced_at_session = self.state.cold_start_session_count
            pending = surfaceable

        # 4. feature introduction events
        events = []
        for feature_id, trigger_fired in session_context.feature_triggers.items():
            event = self.feature_pacing_controller.queue_introduction_if_ready(
                feature_id=feature_id, state=self.state,
                session_context=session_context, trigger_fired=trigger_fired)
            if event:
                events.append(event)

        return MessageDirectives(
            pending_elicitation_question=pending,
            feature_introduction_events=events,
            updated_state=self.state,
        )

    def on_session_end(self, session_context) -> SessionEndResult:
        try:
            result = self.graduation_evaluator.evaluate(self.state)
        except Exception:  # stay in cold start; retry next session (§9)
            logger.exception("graduation evaluation failed; remaining in cold start")
            return SessionEndResult(graduated=False)

        if result.should_graduate:
            try:
                handoff = self.graduation_evaluator.execute_graduation(self.state, self)
                return SessionEndResult(graduated=True, handoff=handoff)
            except Exception:  # never partially activate features (§9)
                logger.exception("graduation handoff failed; remaining in cold start")
                return SessionEndResult(graduated=False)

        return SessionEndResult(
            graduated=False,
            criteria_met=[c.name for c in result.criteria_met],
            criteria_remaining=[c.description for c in result.criteria_failed],
        )

    # ── graduation handoff hooks (wired to the live system in production) ─────
    def deactivate_cold_start_config(self) -> None:
        self.config = None

    def set_personality_drift_gate(self, value: float) -> None:
        self._drift_gate = value

    def activate_proactivity_engine(self) -> None:
        logger.info("proactivity engine activated for user %s", self.user_id)

    def activate_longitudinal_full_mode(self) -> None:
        logger.info("longitudinal full mode activated for user %s", self.user_id)

    def trigger_first_chapter_creation(self, state) -> None:
        logger.info("first narrative chapter created for user %s", self.user_id)

    def deactivate(self) -> None:
        """Self-terminate. Hand full control to the Conversation Orchestrator."""
        self.active = False
        logger.info("Cold Start Engine deactivated for user %s. Graduated at session %d.",
                    self.user_id, self.state.cold_start_session_count)
