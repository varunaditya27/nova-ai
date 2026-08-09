"""Schemas for Layer 9 — Output Delivery & Interaction Orchestration (architecture doc §2-§7).

Pure-stdlib dataclasses + str-enums (the test runtime has no pydantic). These are the shared
contract for the Format Adapter (SC-4), Micro-Interaction Engine (SC-2), Interaction
Orchestrator (SC-1), and Voice & SSML Synthesizer (SC-3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


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


# ── Micro-interaction types (§4.2) ────────────────────────────────────────────
class MicroInteractionType(str, Enum):
    ACKNOWLEDGMENT = "acknowledgment"     # backchannel
    THINKING_INDICATOR = "thinking_indicator"
    EMOTIONAL_PREFIX = "emotional_prefix"
    CORRECTION_INDICATOR = "correction_indicator"
    TRANSITION = "transition"
    CLOSING = "closing"


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
    allow_horizontal_rules: bool = False

    target_length_min_chars: int = 80
    target_length_max_chars: int = 400

    emoji_policy: str = EmojiPolicy.NONE.value
    emoji_position: str = "end_of_sentence"
    max_emojis_per_message: int = 0

    code_format: str = CodeFormat.NONE.value
    language_label_required: bool = False

    voice_mode: bool = False
    voice_content_transform_required: bool = False

    crisis_mode_active: bool = False


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


@dataclass
class FormatFeedbackEvent:
    feedback_text: str
    inferred_preference: str
    timestamp: Optional[Any] = None


# ── Typing / orchestration (§3.5) ─────────────────────────────────────────────
@dataclass
class TypingEvent:
    event_type: str
    delay_before_ms: int = 0
    token: Optional[str] = None
    text: Optional[str] = None
    phrase: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class SelfEditPlan:
    phrase_to_show_then_delete: str
    insert_after_chars: int
    deletion_pause_ms: int
    resume_pause_ms: int


@dataclass
class MicroInteractionPlan:
    acknowledgment: Optional[str] = None
    thinking_indicator: Optional[str] = None
    emotional_prefix: Optional[str] = None
    correction_indicator_armed: bool = False
    transition_phrase: Optional[str] = None
    closing_signal: Optional[str] = None
    any_pre_response_signal: bool = False
    total_pre_response_delay_ms: int = 0


@dataclass
class OrchestratedOutput:
    events: list = field(default_factory=list)
    final_message_text: str = ""
    backchannel_text: Optional[str] = None
    format_spec: Optional[FormatSpec] = None
    voice_ssml: Optional[str] = None
    estimated_render_duration_ms: int = 0
    processing_time_ms: int = 0


# ── Voice (§5) ────────────────────────────────────────────────────────────────
@dataclass
class ProsodyParams:
    rate: str = "medium"
    pitch: str = "+0"


@dataclass
class SSMLDocument:
    ssml: str = ""
    prosody: Optional[ProsodyParams] = None
    fillers_included: bool = False


@dataclass
class AudioResult:
    audio_bytes: bytes = b""
    content_type: str = "audio/mpeg"
    ok: bool = True
    error: Optional[str] = None


# ── Top-level output contract (§7) ────────────────────────────────────────────
@dataclass
class Layer9Output:
    orchestrated_output: Optional[OrchestratedOutput] = None
    final_message_text: str = ""
    format_spec_applied: Optional[FormatSpec] = None

    ssml_document: Optional[str] = None
    audio_result: Optional[AudioResult] = None

    micro_interaction_plan: Optional[MicroInteractionPlan] = None
    backchannel_emitted: Optional[str] = None
    emotional_prefix_emitted: Optional[str] = None

    self_edit_occurred: bool = False
    self_edit_plan: Optional[SelfEditPlan] = None

    voice_mode: bool = False
    total_orchestration_time_ms: int = 0
