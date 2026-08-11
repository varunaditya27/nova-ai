"""Modalities that need no model backend (§5.2): reactions and location pins."""

from __future__ import annotations

from ..schemas import AttachmentPayload, ModalityContext, PrimaryModality

# Reaction emoji → (emotion label, register hint) (§5.2).
REACTION_EMOJI_MAP: dict[str, tuple[str, str]] = {
    "❤️": ("affection_signal", "affection / warmth"),
    "\U0001f602": ("amusement_signal", "amusement / laughter"),   # 😂
    "\U0001f44d": ("approval_signal", "approval / agreement"),    # 👍
    "\U0001f622": ("sadness_signal", "sadness / sympathy"),       # 😢
    "\U0001f621": ("anger_signal", "anger / frustration"),        # 😡
    "\U0001f64f": ("gratitude_signal", "gratitude / pleading"),   # 🙏
    "\U0001f525": ("excitement_signal", "excitement / emphasis"),  # 🔥
}


def map_reaction(emoji: str) -> tuple[str, str]:
    """Map a reaction emoji to (emotion_label, register_hint) (§5.2)."""
    return REACTION_EMOJI_MAP.get(emoji, ("reaction_signal", "an emotional reaction"))


def normalize_reaction(att: AttachmentPayload) -> ModalityContext:
    label, hint = map_reaction(att.reaction_emoji or "")
    return ModalityContext(
        primary_modality=PrimaryModality.REACTION,
        semantic_description=f"User reacted with {att.reaction_emoji or 'a reaction'}",
        emotional_register_hint=hint,
        modality_flags=[label],
    )


def normalize_location(att: AttachmentPayload) -> ModalityContext:
    place = att.place_name or "an unspecified location"
    flags = ["location"]
    if att.place_name is None:
        flags.append("new_location")
    return ModalityContext(
        primary_modality=PrimaryModality.LOCATION,
        location_description=f"Near {place}",
        modality_flags=flags,
    )
