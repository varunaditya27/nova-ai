"""SC-1 — Thinking Pause (architecture doc §3.3, §4.2).

Computes the pause (ms) that fires *before* the typing stream begins — the time Nova appears
to "consider" before responding. Scaled by complexity × emotional intensity, then modulated by
relationship stage and circadian band. Crisis mode and high urgency skip it (calm immediacy).
Randomness is injected (``rng``) so the policy is deterministically testable.
"""

from __future__ import annotations

import random as _random

# Thinking-indicator gate (architecture doc §4.2).
_THINKING_INDICATOR_DISABLED_MODES = {"crisis_support", "technical", "task_help"}
_THINKING_COMPLEXITY_MIN = 0.65
_THINKING_EMOTION_MIN = 0.75


def compute_thinking_pause(
    complexity_score: float,
    emotional_intensity: float,
    urgency_level: float,
    circadian_band: str,
    conversation_mode: str,
    relationship_stage: str,
    crisis_mode_active: bool,
    rng=_random,
) -> int:
    """Return the pre-response thinking pause in ms (0 = none) (architecture doc §3.3)."""
    if crisis_mode_active:
        return 0
    if urgency_level > 0.75:
        return 0

    if complexity_score < 0.3 and emotional_intensity < 0.4:
        base_ms = 0
    elif complexity_score < 0.5 and emotional_intensity < 0.6:
        base_ms = rng.randint(300, 700)
    elif complexity_score < 0.7 or emotional_intensity < 0.7:
        base_ms = rng.randint(700, 1600)
    else:
        base_ms = rng.randint(1600, 3200)

    # Early-stage relationships → less visible hesitation (more polished).
    if relationship_stage in ("stranger", "acquaintance"):
        base_ms = int(base_ms * 0.70)

    # Circadian modifier.
    if circadian_band == "late_night":
        base_ms = int(base_ms * 1.25)
    elif circadian_band == "morning":
        base_ms = int(base_ms * 0.85)

    return max(0, base_ms)


def should_show_thinking_indicator(
    complexity_score: float, emotional_intensity: float, conversation_mode: str
) -> bool:
    """Whether to prepend a thinking-indicator phrase to the pause (architecture doc §4.2)."""
    if conversation_mode in _THINKING_INDICATOR_DISABLED_MODES:
        return False
    return (complexity_score >= _THINKING_COMPLEXITY_MIN
            or emotional_intensity >= _THINKING_EMOTION_MIN)
