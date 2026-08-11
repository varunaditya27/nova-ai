"""Layer 9 enums — format, typing-event, and micro-interaction types (§2-§4)."""

from __future__ import annotations

from enum import Enum


# ── Format enums (§6.2) ───────────────────────────────────────────────────────
class Register(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    INTIMATE = "intimate"


class Structure(str, Enum):
    PURE_PROSE = "pure_prose"
    PROSE_WITH_BREAKS = "prose_with_breaks"
    LIGHT_LIST = "light_list"
    STRUCTURED_LIST = "structured_list"
    TABLE = "table"


class EmojiPolicy(str, Enum):
    NONE = "none"
    RARE = "rare"
    NATURAL = "natural"
    FREQUENT = "frequent"


class CodeFormat(str, Enum):
    NONE = "none"
    INLINE_ONLY = "inline_only"
    FULL_BLOCKS = "full_blocks"


class LengthPreference(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


# ── Event types (§3.5) ────────────────────────────────────────────────────────
class TypingEventType(str, Enum):
    THINKING_PAUSE = "thinking_pause"
    START_TYPING = "start_typing"
    TOKEN = "token"
    PAUSE = "pause"
    SHOW_PHRASE = "show_phrase"
    DELETE_PHRASE = "delete_phrase"
    RESUME_TYPING = "resume_typing"
    SEND_MESSAGE = "send_message"
    BACKCHANNEL = "backchannel"
