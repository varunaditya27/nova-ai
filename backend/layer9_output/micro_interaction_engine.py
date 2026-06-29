"""SC-2 — Micro-Interaction Engine (architecture doc §4.2-§4.3).

Plans the sub-response behavioral signals that make Nova feel like a presence rather than a
text generator. The doc specifies **six types**, each with a trigger, a relationship-stage gate,
and a frequency cap:

    1. Acknowledgment (backchannel)  4. Correction indicator (armed)
    2. Thinking indicator            5. Transition phrase
    3. Emotional prefix              6. Closing signal

Deterministic (selection via injected ``rng``). Crisis mode is a hard override that suppresses
every micro-interaction. (Reconciliation: the May-28 scaffold listed a different six-type set —
backchannel/affirmation/empathy/uncertainty/thinking/warmth — the authoritative doc taxonomy is
implemented instead.)
"""

from __future__ import annotations

import random as _random

from backend.layer9_output.schemas import MicroInteractionPlan

# ── Type 1: Acknowledgment tokens (§4.2) ─────────────────────────────────────
ACKNOWLEDGMENT_TOKENS = {
    "neutral":    ["Hmm.", "I see.", "Got it.", "Okay.", "Yeah."],
    "empathetic": ["Ah.", "Oh.", "Mm.", "I hear that."],
    "engaged":    ["Right.", "Makes sense.", "Okay, okay."],
    "thoughtful": ["Hmm, okay.", "Let me read this carefully."],
}
_ACK_DISABLED_MODES = {"crisis_support", "task_help", "technical"}
_ACK_STAGES = {"acquaintance", "friend", "close_friend"}
_ACK_MIN_GAP = 4               # max 1 acknowledgment per 4 user messages
_ACK_DELAY_MS = 600

# ── Type 2: Thinking indicators (§4.2) ───────────────────────────────────────
THINKING_INDICATOR_PHRASES = [
    "Give me a second.", "Let me think about that.", "Hmm, that's a good one.",
    "One sec.", "Okay, thinking.", "Let me sit with that for a moment.",
]
_THINKING_DISABLED_MODES = {"crisis_support", "technical", "task_help"}

# ── Type 3: Emotional prefixes (§4.2) ────────────────────────────────────────
EMOTIONAL_PREFIXES = {
    "celebration":     ["Oh wow.", "That's great.", "Oh nice!", "Hey, that's huge."],
    "empathy":         ["Ah, that's rough.", "Oh, I'm sorry.", "Oof.", "That's a lot."],
    "surprise":        ["Oh.", "Oh wow.", "Wait, really?"],
    "received_thanks": ["Ah, of course.", "Oh, glad it helped."],
}
_PREFIX_DISABLED_MODES = {"crisis_support", "technical", "task_help"}
_PREFIX_TURN_TYPES = {"sharing_news", "venting", "expressing_gratitude"}
_PREFIX_STAGES = {"friend", "close_friend"}
_PREFIX_MAX_CHARS = 20
_PREFIX_DELAY_MS = 500

# ── Type 4: Correction indicators (§4.2) ─────────────────────────────────────
_CORRECTION_DISABLED_MODES = {"crisis_support", "task_help"}
_CORRECTION_STAGES = {"acquaintance", "friend", "close_friend"}

# ── Type 5: Transition phrases (§4.2) ────────────────────────────────────────
TRANSITION_PHRASES = {
    "proactive_initiation": ["Hey, quick thing —", "Oh, I wanted to ask —", "Before I forget —"],
    "topic_change":         ["Okay, different question —", "Actually, while we're on this —"],
}

# ── Type 6: Closing signals (§4.2) ───────────────────────────────────────────
CLOSING_SIGNAL_PHRASES = [
    "Alright, I'll let you get to it.", "Good luck with it — let me know how it goes.",
    "Talk later.", "Hope it goes well.", "Take care.",
]
_CLOSING_STAGES = {"friend", "close_friend"}


def plan_micro_interactions(
    conversation_mode: str,
    relationship_stage: str,
    emotional_intensity: float,
    turn_type: str,
    user_message_length: int = 0,
    consecutive_user_messages: int = 0,
    complexity_score: float = 0.0,
    messages_since_last_ack: int = 99,
    correction_armed: bool = False,
    is_proactive: bool = False,
    farewell_detected: bool = False,
    crisis_mode_active: bool = False,
    rng=_random,
) -> MicroInteractionPlan:
    """Assemble the MicroInteractionPlan for this turn (architecture doc §4.3)."""
    plan = MicroInteractionPlan()

    # Crisis is a hard override — suppress everything (§2).
    if crisis_mode_active or conversation_mode == "crisis_support":
        return plan

    # Type 1 — Acknowledgment.
    ack_triggered = (user_message_length > 400 or consecutive_user_messages >= 2
                     or emotional_intensity >= 0.7)
    if (ack_triggered and conversation_mode not in _ACK_DISABLED_MODES
            and relationship_stage in _ACK_STAGES
            and messages_since_last_ack >= _ACK_MIN_GAP):
        category = "empathetic" if emotional_intensity >= 0.7 else "neutral"
        plan.acknowledgment = rng.choice(ACKNOWLEDGMENT_TOKENS[category])

    # Type 2 — Thinking indicator.
    if (conversation_mode not in _THINKING_DISABLED_MODES
            and (complexity_score >= 0.65 or emotional_intensity >= 0.75)):
        plan.thinking_indicator = rng.choice(THINKING_INDICATOR_PHRASES)

    # Type 3 — Emotional prefix.
    if (emotional_intensity >= 0.65 and turn_type in _PREFIX_TURN_TYPES
            and conversation_mode not in _PREFIX_DISABLED_MODES
            and relationship_stage in _PREFIX_STAGES):
        category = "celebration" if turn_type == "sharing_news" else (
            "received_thanks" if turn_type == "expressing_gratitude" else "empathy")
        candidates = [p for p in EMOTIONAL_PREFIXES[category] if len(p) <= _PREFIX_MAX_CHARS]
        if candidates:
            plan.emotional_prefix = rng.choice(candidates)

    # Type 4 — Correction indicator (armed by Layer 4's revised-conclusion signal).
    if (correction_armed and conversation_mode not in _CORRECTION_DISABLED_MODES
            and relationship_stage in _CORRECTION_STAGES):
        plan.correction_indicator_armed = True

    # Type 5 — Transition (mandatory for proactive initiation).
    if is_proactive:
        plan.transition_phrase = rng.choice(TRANSITION_PHRASES["proactive_initiation"])

    # Type 6 — Closing signal.
    if (farewell_detected and relationship_stage in _CLOSING_STAGES):
        plan.closing_signal = rng.choice(CLOSING_SIGNAL_PHRASES)

    # Aggregate pre-response signal flags (§4.3).
    delay = 0
    if plan.acknowledgment:
        delay += _ACK_DELAY_MS
    if plan.emotional_prefix:
        delay += _PREFIX_DELAY_MS
    plan.total_pre_response_delay_ms = delay
    plan.any_pre_response_signal = bool(plan.acknowledgment or plan.emotional_prefix)
    return plan
