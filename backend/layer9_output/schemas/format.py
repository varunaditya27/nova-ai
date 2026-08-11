"""FormatSpec + UserFormatProfile — the Format Adapter (SC-4) contract (§6.2, §6.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.layer9_output.schemas.enums import (
    CodeFormat,
    EmojiPolicy,
    LengthPreference,
    Register,
    Structure,
)


# ── FormatSpec (§6.2) ─────────────────────────────────────────────────────────
@dataclass
class FormatSpec:
    register: str = Register.CASUAL.value
    use_contractions: bool = True
    allow_fragments: bool = False
    allow_slang: bool = False

    structure: str = Structure.PROSE_WITH_BREAKS.value
    max_list_items: int = 0
    allow_headers: bool = False
    allow_bold: bool = False

    target_length_min_chars: int = 80
    target_length_max_chars: int = 400

    emoji_policy: str = EmojiPolicy.NONE.value
    max_emojis_per_message: int = 0

    code_format: str = CodeFormat.NONE.value
    language_label_required: bool = False

    voice_mode: bool = False
    voice_content_transform_required: bool = False

    crisis_mode_active: bool = False


@dataclass
class FormatFeedbackEvent:
    feedback_text: str
    inferred_preference: str
    timestamp: Optional[Any] = None


# ── User Format Profile (§6.5) ────────────────────────────────────────────────
@dataclass
class UserFormatProfile:
    user_id: str = ""
    updated_at: Optional[Any] = None
    version: int = 0

    preferred_length: str = LengthPreference.MEDIUM.value
    emoji_usage_rate: float = 0.0
    uses_slang_themselves: bool = False
    avg_user_message_length: float = 0.0

    always_brief: bool = False
    prefers_bullets: bool = False
    prefers_no_markdown: bool = False
    explicit_length_preference: Optional[str] = None

    explicit_format_feedback_events: list[FormatFeedbackEvent] = field(default_factory=list)

    # Bookkeeping for the cross-turn skim-detection signal (§6.6): the length of Nova's most
    # recently delivered response, so the NEXT turn's writer can compare it against this turn's
    # user reply latency/length without querying another store.
    last_response_length: int = 0
    last_response_at: Optional[Any] = None
