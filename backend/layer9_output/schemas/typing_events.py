"""Typing/orchestration event contracts — Interaction Orchestrator SC-1 (§3.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.layer9_output.schemas.format import FormatSpec


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
