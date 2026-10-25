"""Layer 13 SC-2 — Cold Start Handling (architecture doc §5).

When a new user opens Nova, every component is seeded with population-center defaults (not
arbitrary values, but statistically-grounded starting points). `make_initial_state()` is the
factory (never share mutable defaults across users). `ColdStartContextBuilder.process_message()`
runs in parallel with the normal pipeline, aggressively turning each message into InitialState
updates via the PassiveElicitationEngine. Personality drift is deliberately slow during cold
start (gated to 30%) because there is not yet enough data to update confidently.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from .passive_elicitation import PassiveElicitationEngine
from .schemas import (
    ColdStartBehaviorConfig,
    CommunicationStyleProfile,
    InitialState,
    InitialStateUpdate,
    PersonalityVector,
)

FIRST_MESSAGE_TEMPLATE = (
    "Hey. I'm Nova — not much to say as an intro, honestly. "
    "The best way to figure out what this is for you is just to start talking. "
    "What's on your mind?"
)
_FIRST_MESSAGE_LATE_NIGHT = (
    "Hey. I'm Nova. It's late — you must have something on your mind. What's going on?"
)
_FIRST_MESSAGE_FALLBACK = "Hey. What's on your mind?"

# "my name is X" / "call me X" are unambiguous in any case. "I'm X" / "I am X" only count when X is
# capitalised ("I'm Arjun") — and not a capitalised state word ("I'm Sorry") — since case-insensitive
# matching made "I'm tired" register "tired" as the user's name.
_NAME_INTRO_RE = re.compile(
    r"(?:(?i:my name is|call me)\s+([A-Za-z]+)|\b(?:I'm|I am)\s+([A-Z][a-z]+)\b)")
_NOT_NAMES = {"sorry", "fine", "good", "great", "tired", "happy", "sad", "not", "just", "here", "back",
              "done", "okay", "sure", "ready", "glad", "worried", "scared", "stressed", "hungry",
              "bored", "lost", "alone", "late", "trying", "going", "feeling", "really", "very", "so"}


def extract_name(message: str):
    for m in _NAME_INTRO_RE.finditer(message):
        name = m.group(1) or m.group(2)
        if name.lower() not in _NOT_NAMES:
            return name.capitalize()
    return None


def make_initial_state(user_id: str) -> InitialState:
    """Seed a fresh InitialState with population-center defaults (§5.1)."""
    return InitialState(user_id=user_id, initialized_at=datetime.now(timezone.utc))


def generate_first_message(time_of_day: Optional[str] = None) -> str:
    """Persona-shaped opener. Core content fixed by the template; on any failure → fallback (§9)."""
    try:
        if time_of_day == "late_night":
            return _FIRST_MESSAGE_LATE_NIGHT
        if time_of_day is None:
            raise ValueError("missing circadian band")
        return FIRST_MESSAGE_TEMPLATE
    except Exception:
        return _FIRST_MESSAGE_FALLBACK


class ColdStartContextBuilder:
    """Processes every message for context signals more aggressively than normal operation."""

    def __init__(self, passive_engine: Optional[PassiveElicitationEngine] = None):
        self.passive_engine = passive_engine or PassiveElicitationEngine()

    def process_message(self, message: str, message_index: int, session_number: int,
                        timestamp, initial_state: InitialState,
                        session_history: list) -> InitialStateUpdate:
        signals = self.passive_engine.extract(
            message=message, message_index=message_index, session_number=session_number,
            timestamp=timestamp, session_history=session_history)
        updates: dict = {}

        # ── user handle ──────────────────────────────────────────────────────
        if initial_state.user_handle is None:
            name = extract_name(message)
            if name:
                updates["user_handle"] = name

        # ── life phase (only above the confidence threshold) ─────────────────
        lc = signals.life_context_signals
        if initial_state.life_phase is None and lc.life_phase_confidence > 0.50:
            updates["life_phase"] = lc.life_phase_signal
            updates["new_semantic_facts"] = [{
                "fact_id": str(uuid.uuid4()),
                "category": "life_context",
                "fact_text": f"User is likely a {lc.life_phase_signal}",
                "confidence": lc.life_phase_confidence,
                "derived_from": "passive_cold_start_extraction",
            }]

        # ── communication style profile (needs a few messages) ───────────────
        if message_index >= 3 and initial_state.communication_style_profile is None:
            updates["communication_style_profile"] = CommunicationStyleProfile(
                verbosity_preference=signals.communication_style.verbosity_preference,
                formality_level=self._infer_formality(signals.vocabulary_register),
                emoji_comfort=signals.vocabulary_register.uses_emoji,
                disclosure_comfort=signals.self_disclosure_comfort.level,
                emotional_expression_style=signals.emotional_expression_style.style,
            )

        # ── personality vector drift (gated by the cold-start multiplier) ────
        drift = self._compute_personality_vector_update(
            signals, initial_state.personality_vector,
            ColdStartBehaviorConfig.personality_drift_gate_multiplier)
        if drift:
            updates["personality_vector_drift"] = drift

        # ── named relationships (dedupe against what's already known) ────────
        new_people = [p for p in signals.named_entities
                      if not any(p.name == e.name for e in initial_state.named_relationships)]
        if new_people:
            updates["new_named_relationships"] = new_people

        return InitialStateUpdate(updates=updates)

    def _infer_formality(self, vocab) -> str:
        if vocab.formality_delta < -1:
            return "casual"
        if vocab.formality_delta > 1:
            return "formal"
        return "neutral"

    def _compute_personality_vector_update(self, signals, current_pv: PersonalityVector,
                                           cold_start_gate: float) -> dict:
        updates: dict = {}
        vocab = signals.vocabulary_register
        comm = signals.communication_style

        target_verbosity = {"concise": 0.25, "medium": 0.45, "verbose": 0.70}.get(
            comm.verbosity_preference, current_pv.verbosity)
        if abs(target_verbosity - current_pv.verbosity) > 0.05:
            step = (target_verbosity - current_pv.verbosity) * 0.10 * cold_start_gate
            updates["verbosity"] = current_pv.verbosity + step

        if vocab.formality_delta < -2 and current_pv.formality > 0.30:
            updates["formality"] = current_pv.formality - 0.05 * cold_start_gate
        elif vocab.formality_delta > 2 and current_pv.formality < 0.70:
            updates["formality"] = current_pv.formality + 0.05 * cold_start_gate

        return updates
