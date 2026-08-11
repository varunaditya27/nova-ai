"""Schemas for Layer 9 — Output Delivery & Interaction Orchestration (architecture doc §2-§7).

Pure-stdlib dataclasses + str-enums (the test runtime has no pydantic). These are the shared
contract for the Format Adapter (SC-4), Micro-Interaction Engine (SC-2), Interaction
Orchestrator (SC-1), and Voice & SSML Synthesizer (SC-3).
"""

from __future__ import annotations

from backend.layer9_output.schemas.enums import (
    CodeFormat,
    EmojiPolicy,
    LengthPreference,
    Register,
    Structure,
    TypingEventType,
)
from backend.layer9_output.schemas.format import (
    FormatFeedbackEvent,
    FormatSpec,
    UserFormatProfile,
)
from backend.layer9_output.schemas.output import Layer9Output
from backend.layer9_output.schemas.typing_events import (
    MicroInteractionPlan,
    OrchestratedOutput,
    SelfEditPlan,
    TypingEvent,
)
from backend.layer9_output.schemas.voice import (
    AudioResult,
    ProsodyParams,
    SSMLDocument,
    TranscriptResult,
)

__all__ = [
    "Register", "Structure", "EmojiPolicy", "CodeFormat", "LengthPreference",
    "TypingEventType",
    "FormatSpec", "FormatFeedbackEvent", "UserFormatProfile",
    "TypingEvent", "SelfEditPlan", "MicroInteractionPlan", "OrchestratedOutput",
    "ProsodyParams", "SSMLDocument", "AudioResult", "TranscriptResult",
    "Layer9Output",
]
