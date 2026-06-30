"""Conversation Orchestrator — the entry point for a user turn.

Pure orchestration: this module owns the *sequence* in which the 13 layers run and the
cross-cutting invariants, but no business logic of its own — every layer step is injected as a
callable (`PipelineSteps`), so the orchestrator is fully testable offline and a refactor inside a
layer never changes this file. In production the steps are thin adapters around each layer's
public entry point (Layer 1 `service`, Layer 2 `memory_arbiter`, Layer 3 `build_emotion_intent_packet`,
Layer 4 persona/4a/4b, Layer 9 `deliver`, Layer 11 `SafetyAgent`, Layer 13 `ColdStartEngine`, …).

Invariants enforced here (see docs/NOVA_AI_MASTER_ARCHITECTURE.md):
  - Layer 11 (safety) runs first and is **never blocked** — even if a later layer raises.
  - Crisis veto: if SC-2 detects a crisis OR Layer 3 raised the crisis flag, SC-3 escalation
    replaces the normal response entirely; System 1/2 generation is skipped.
  - Layer 13 cold-start overlay is applied after Layer 2 (proactivity observe-only, drift gate,
    pending elicitation surfaced).
  - System 1 / System 2 routing from Layer 3's mode + complexity.
  - Confabulation guard: empty recall flags downstream not to invent memories.
  - Layer 9 always runs (crisis → pure prose, micro-interactions suppressed).
  - The post-turn state update is the final step and never blocks the response path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Modes whose emotional/cognitive weight always warrants the full System 2 path.
_SYSTEM2_MODES = frozenset({
    "crisis", "emotional_support", "goal_planning", "life_review", "social_coaching",
})
_CRISIS_FALLBACK = ("I'm here with you. If you're in immediate danger, please contact your local "
                    "emergency number or a crisis line right now.")


@dataclass
class PipelineSteps:
    """Injectable layer entry points. All optional; production wires real layer adapters."""
    perceive: Optional[Callable] = None         # L1  (user_id, message, now) -> input_packet
    recall: Optional[Callable] = None           # L2  (user_id, input_packet) -> list[memory]
    cold_start: Optional[Callable] = None       # L13 (user_id, message) -> directives | None
    classify: Optional[Callable] = None         # L3  (message, input_packet, recalled) -> EI
    safety_scan: Optional[Callable] = None      # L11 SC-2 (user_id, message, input_packet) -> CA
    build_persona: Optional[Callable] = None    # L4  (ctx) -> persona_packet
    plan: Optional[Callable] = None             # L4a (ctx) -> draft
    refine: Optional[Callable] = None           # L4b (ctx, draft) -> refined
    guardrails: Optional[Callable] = None       # L11 SC-1 (ctx, response) -> result
    escalate: Optional[Callable] = None         # L11 SC-3 (ctx, crisis) -> crisis response
    deliver: Optional[Callable] = None          # L9  (ctx, response, crisis_mode_active) -> out
    state_update: Optional[Callable] = None     # post-turn (ctx) -> None


@dataclass
class TurnContext:
    user_id: str
    message: str
    now: datetime
    session_id: str = ""
    input_packet: Any = None
    recalled_memories: list = field(default_factory=list)
    confabulation_guard: bool = False
    cold_start_active: bool = False
    cold_start_directives: Any = None
    proactivity_mode: str = "normal"
    personality_drift_gate: float = 1.0
    pending_elicitation: Any = None
    emotion_intent: Any = None
    conversation_mode: str = "casual"
    cognitive_system: str = "system1"
    persona_packet: Any = None
    semantic_draft: str = ""
    response_text: str = ""
    refined: bool = False
    crisis_active: bool = False
    crisis_tier: Any = None
    crisis_assessment: Any = None
    guardrail_flags: list = field(default_factory=list)
    delivered: Any = None
    degraded: bool = False
    layers_run: list = field(default_factory=list)
    state_updated: bool = False


@dataclass
class OrchestratedOutput:
    response_text: str
    delivered: Any
    cognitive_system: str
    conversation_mode: str
    refined: bool
    crisis_active: bool
    crisis_tier: Any
    confabulation_guard: bool
    cold_start_active: bool
    proactivity_mode: str
    pending_elicitation: Any
    guardrail_flags: list
    degraded: bool
    state_updated: bool
    layers_run: list


def route_system(emotion_intent) -> str:
    """System 2 for emotionally/cognitively heavy turns; System 1 otherwise (§ dual-pipeline)."""
    mode = getattr(emotion_intent, "mode", "casual")
    complexity = getattr(emotion_intent, "complexity", "simple")
    if mode in _SYSTEM2_MODES or complexity == "complex":
        return "system2"
    return "system1"


def run_system1(ctx: TurnContext, steps: PipelineSteps) -> None:
    """Fast path: persona + Agent 4a only (Emotion Refiner skipped)."""
    ctx.persona_packet = steps.build_persona(ctx)
    ctx.semantic_draft = steps.plan(ctx)
    ctx.response_text = ctx.semantic_draft
    ctx.refined = False


def run_system2(ctx: TurnContext, steps: PipelineSteps) -> None:
    """Full path: persona + Agent 4a + Agent 4b (Emotion Refiner)."""
    ctx.persona_packet = steps.build_persona(ctx)
    ctx.semantic_draft = steps.plan(ctx)
    ctx.response_text = steps.refine(ctx, ctx.semantic_draft)
    ctx.refined = True


class ConversationOrchestrator:
    def __init__(self, steps: PipelineSteps):
        self.steps = steps

    def run_turn(self, user_id: str, message: str, now: Optional[datetime] = None,
                 session_id: str = "") -> OrchestratedOutput:
        s = self.steps
        ctx = TurnContext(user_id=user_id, message=message,
                          now=now or datetime.now(timezone.utc), session_id=session_id)

        # ── Layer 11 SC-2: crisis detection runs first and is NEVER blocked ──
        ctx.crisis_assessment = self._safe_safety_scan(ctx)

        try:
            # ── Layer 1: input perception ───────────────────────────────────
            ctx.input_packet = s.perceive(user_id, message, ctx.now)
            ctx.layers_run.append("layer1_input")

            # ── Layer 2: memory recall (read-only during inference) ─────────
            ctx.recalled_memories = s.recall(user_id, ctx.input_packet) or []
            ctx.confabulation_guard = len(ctx.recalled_memories) == 0   # invariant
            ctx.layers_run.append("layer2_memory")

            # ── Layer 13: cold-start overlay (applied after Layer 2) ────────
            self._apply_cold_start_overlay(ctx)

            # ── Layer 3: emotion + intent classification, mode resolution ───
            ctx.emotion_intent = s.classify(message, ctx.input_packet, ctx.recalled_memories)
            ctx.conversation_mode = getattr(ctx.emotion_intent, "mode", "casual")
            ctx.layers_run.append("layer3_reasoning")

            # ── Crisis veto (OR of SC-2 and Layer 3 crisis flag) ────────────
            if self._is_crisis(ctx):
                self._handle_crisis(ctx)
            else:
                self._generate_normal(ctx)
        except Exception:  # main path failed — degrade safely; safety already captured
            logger.exception("conversation pipeline failed; delivering degraded response")
            ctx.degraded = True
            if not ctx.response_text:
                ctx.response_text = (_CRISIS_FALLBACK if self._is_crisis(ctx)
                                     else "Sorry — I lost my footing there. Could you say that again?")

        # ── Layer 9: always deliver (crisis → pure prose) ───────────────────
        ctx.delivered = self._safe_deliver(ctx)

        # ── Post-turn state update (final; never blocks the response) ────────
        self._safe_state_update(ctx)

        return self._to_output(ctx)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _safe_safety_scan(self, ctx: TurnContext):
        try:
            assessment = self.steps.safety_scan(ctx.user_id, ctx.message, ctx.input_packet)
            ctx.layers_run.append("layer11_safety")
            return assessment
        except Exception:  # safety must never break the turn; treat as non-crisis but log loudly
            logger.exception("safety scan failed — defaulting to non-crisis (still never blocked)")
            ctx.layers_run.append("layer11_safety")
            return None

    def _apply_cold_start_overlay(self, ctx: TurnContext) -> None:
        if self.steps.cold_start is None:
            return
        directives = self.steps.cold_start(ctx.user_id, ctx.message)
        ctx.layers_run.append("layer13_onboarding")
        if directives is None:
            return
        ctx.cold_start_active = True
        ctx.cold_start_directives = directives
        ctx.proactivity_mode = getattr(directives, "proactivity_mode", "observe_only")
        ctx.personality_drift_gate = getattr(directives, "personality_drift_gate", 0.30)
        ctx.pending_elicitation = getattr(directives, "pending_elicitation", None)

    def _is_crisis(self, ctx: TurnContext) -> bool:
        sc2 = bool(getattr(ctx.crisis_assessment, "is_crisis", False))
        l3 = bool(getattr(ctx.emotion_intent, "crisis_flag", False))
        return sc2 or l3

    def _handle_crisis(self, ctx: TurnContext) -> None:
        ctx.crisis_active = True
        ctx.crisis_tier = getattr(ctx.crisis_assessment, "tier", None)
        ctx.response_text = self.steps.escalate(ctx, ctx.crisis_assessment)   # SC-3 replaces output
        ctx.layers_run.append("layer11_escalation")

    def _generate_normal(self, ctx: TurnContext) -> None:
        ctx.cognitive_system = route_system(ctx.emotion_intent)
        if ctx.cognitive_system == "system1":
            run_system1(ctx, self.steps)
        else:
            run_system2(ctx, self.steps)
        ctx.layers_run.append("layer4_persona")
        # Layer 11 SC-1: post-generation ethical guardrails
        if self.steps.guardrails is not None:
            result = self.steps.guardrails(ctx, ctx.response_text)
            ctx.layers_run.append("layer11_guardrails")
            if not getattr(result, "approved", True):
                ctx.response_text = getattr(result, "replacement", None) or ctx.response_text
                ctx.guardrail_flags = list(getattr(result, "flags", []) or [])

    def _safe_deliver(self, ctx: TurnContext):
        try:
            out = self.steps.deliver(ctx, ctx.response_text, ctx.crisis_active)
            ctx.layers_run.append("layer9_output")
            return out
        except Exception:
            logger.exception("delivery failed")
            ctx.degraded = True
            return None

    def _safe_state_update(self, ctx: TurnContext) -> None:
        if self.steps.state_update is None:
            return
        try:
            self.steps.state_update(ctx)
            ctx.state_updated = True
            ctx.layers_run.append("state_update")
        except Exception:  # post-turn writes must never affect the delivered response
            logger.exception("post-turn state update failed")

    def _to_output(self, ctx: TurnContext) -> OrchestratedOutput:
        return OrchestratedOutput(
            response_text=ctx.response_text, delivered=ctx.delivered,
            cognitive_system=ctx.cognitive_system, conversation_mode=ctx.conversation_mode,
            refined=ctx.refined, crisis_active=ctx.crisis_active, crisis_tier=ctx.crisis_tier,
            confabulation_guard=ctx.confabulation_guard, cold_start_active=ctx.cold_start_active,
            proactivity_mode=ctx.proactivity_mode, pending_elicitation=ctx.pending_elicitation,
            guardrail_flags=ctx.guardrail_flags, degraded=ctx.degraded,
            state_updated=ctx.state_updated, layers_run=ctx.layers_run)
