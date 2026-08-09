"""SC-4 — User Format Profile (architecture doc §6.5-§6.6).

A persistent per-user record of learned format preferences. Format preferences are *learned*,
not set: after each delivered response the Orchestrator feeds three engagement signals
(latency after long responses, user/Nova message-length ratio, explicit feedback) back here.
Deterministic; persisted via ``infra.db.models.output_prefs.UserFormatProfile``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer9_output.format_adapter import _EMOJI_RE
from backend.layer9_output.schemas import (
    FormatFeedbackEvent,
    LengthPreference,
    UserFormatProfile,
)
# Reuse Layer 4's real, already-tested casual-language regex rather than inventing a second
# slang detector -- style_learning.py already classifies exactly this signal for its own
# formality_preference EMA.
from backend.layer4_persona.style_learning import _CASUAL as _SLANG_RE

_ORDER = [LengthPreference.SHORT.value, LengthPreference.MEDIUM.value, LengthPreference.LONG.value]
_ENGAGEMENT_EMA = 0.2   # gentle -- one message never swings emoji_usage_rate/avg length far


def initialize_defaults(user_id: str) -> UserFormatProfile:
    """A fresh profile with global defaults (architecture doc §6.5)."""
    return UserFormatProfile(user_id=user_id, preferred_length=LengthPreference.MEDIUM.value,
                             emoji_usage_rate=0.0, version=0)


def shift_preference_shorter(pref: str) -> str:
    i = _ORDER.index(pref) if pref in _ORDER else 1
    return _ORDER[max(0, i - 1)]


def classify_format_feedback(text: str) -> Optional[str]:
    """Map an explicit format remark to a preference (architecture doc §6.6)."""
    low = (text or "").lower()
    if any(k in low for k in ("list", "bullet", "bullets")):
        return "bullets"
    if any(k in low for k in ("no markdown", "write normally", "plain", "just text")):
        return "no_markdown"
    if any(k in low for k in ("concise", "shorter", "brief", "short version", "tldr", "tl;dr")):
        return "short"
    if any(k in low for k in ("more detail", "longer", "elaborate", "tell me more", "in depth")):
        return "long"
    return None


def apply_explicit_override(profile: UserFormatProfile, preference: Optional[str]) -> None:
    if preference == "short":
        profile.always_brief = True
        profile.explicit_length_preference = LengthPreference.SHORT.value
        profile.preferred_length = LengthPreference.SHORT.value
    elif preference == "long":
        profile.explicit_length_preference = LengthPreference.LONG.value
        profile.preferred_length = LengthPreference.LONG.value
    elif preference == "bullets":
        profile.prefers_bullets = True
    elif preference == "no_markdown":
        profile.prefers_no_markdown = True


def update_format_profile(
    profile: UserFormatProfile,
    nova_response_length: int,
    user_response_latency_ms: int,
    user_response_length: int,
    explicit_format_feedback: Optional[str] = None,
    user_message_text: str = "",
) -> UserFormatProfile:
    """Fold engagement signals into the profile (architecture doc §6.6)."""
    # Signal 1: fast reply after a long response → user likely skimmed → prefer shorter.
    if nova_response_length > 400 and user_response_latency_ms < 3000:
        profile.preferred_length = shift_preference_shorter(profile.preferred_length)

    # Signal 2: user reply much shorter than Nova's → prefer shorter.
    if nova_response_length > 0 and user_response_length < nova_response_length * 0.15:
        profile.preferred_length = shift_preference_shorter(profile.preferred_length)

    # Signal 3: explicit feedback overrides.
    if explicit_format_feedback:
        preference = classify_format_feedback(explicit_format_feedback)
        profile.explicit_format_feedback_events.append(FormatFeedbackEvent(
            feedback_text=explicit_format_feedback, inferred_preference=preference,
            timestamp=datetime.utcnow()))
        apply_explicit_override(profile, preference)

    # Signal 4: the user's own emoji/slang/length habits -- these three fields were declared on
    # the schema and consumed downstream by format_adapter.compute_format_spec's emoji-policy and
    # allow_slang decisions, but nothing here ever computed them, so those decisions silently
    # never engaged (emoji_usage_rate pinned at 0.0 -> always EmojiPolicy.NONE, uses_slang_
    # themselves pinned at False -> allow_slang always False).
    if user_response_length > 0:
        profile.avg_user_message_length = (
            (1.0 - _ENGAGEMENT_EMA) * profile.avg_user_message_length
            + _ENGAGEMENT_EMA * user_response_length)
    if user_message_text:
        used_emoji = 1.0 if _EMOJI_RE.search(user_message_text) else 0.0
        profile.emoji_usage_rate = (
            (1.0 - _ENGAGEMENT_EMA) * profile.emoji_usage_rate + _ENGAGEMENT_EMA * used_emoji)
        if _SLANG_RE.search(user_message_text):
            profile.uses_slang_themselves = True

    profile.version += 1
    profile.updated_at = datetime.utcnow()
    return normalize(profile)


def normalize(profile: UserFormatProfile) -> UserFormatProfile:
    """Clamp learned values into valid ranges (architecture doc §6.5)."""
    profile.emoji_usage_rate = max(0.0, min(1.0, profile.emoji_usage_rate))
    profile.avg_user_message_length = max(0.0, profile.avg_user_message_length)
    if profile.preferred_length not in _ORDER:
        profile.preferred_length = LengthPreference.MEDIUM.value
    return profile
