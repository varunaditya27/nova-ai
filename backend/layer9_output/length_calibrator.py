"""SC-1 — Length Calibrator (architecture doc §3.6).

Computes a ``(min_chars, max_chars)`` target that bounds the Layer 4 response. Response length
is a *social signal*, not just information density — so the target is computed here and passed
**upstream to Layer 4 before generation**, rather than truncating after the fact. Deterministic.
"""

from __future__ import annotations

# Base char ranges per conversation mode (architecture doc §3.6).
BASE_RANGES = {
    "casual_chat":       (40, 180),
    "task_help":         (100, 600),
    "emotional_support": (60, 250),
    "crisis_support":    (80, 220),
    "deep_reasoning":    (200, 800),
    "technical":         (150, 700),
    "celebration":       (60, 200),
}
_HARD_MAX = 1200


def compute_length_target(
    conversation_mode: str,
    emotional_intensity: float,
    content_type: str,
    turn_type: str,
    relationship_stage: str,
    user_preferred_length: str,
) -> tuple[int, int]:
    """Return the (min_chars, max_chars) length target for Layer 4 (architecture doc §3.6)."""
    min_c, max_c = BASE_RANGES.get(conversation_mode, (80, 400))

    # Turn-type modifiers.
    if turn_type == "venting":
        max_c = min(max_c, 200)
    elif turn_type == "question":
        max_c = min(max_c, 180)
    elif turn_type == "request_advice":
        min_c = max(min_c, 120)
    elif turn_type == "sharing_news":
        max_c = min(max_c, 200)

    # Emotional intensity: high distress → shorter, more space for them.
    if emotional_intensity > 0.70:
        max_c = int(max_c * 0.65)

    # Relationship modifier.
    if relationship_stage in ("stranger", "acquaintance"):
        min_c = max(min_c, 100)
    elif relationship_stage == "close_friend":
        min_c = max(20, min_c // 2)

    # User preference override.
    if user_preferred_length == "short":
        max_c = int(max_c * 0.65)
    elif user_preferred_length == "long":
        max_c = int(max_c * 1.40)

    return (min_c, min(max_c, _HARD_MAX))
