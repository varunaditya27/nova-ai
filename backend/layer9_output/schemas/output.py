"""Layer9Output — the top-level per-turn output contract (§7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.layer9_output.schemas.format import FormatSpec
from backend.layer9_output.schemas.typing_events import (
    MicroInteractionPlan,
    OrchestratedOutput,
    SelfEditPlan,
)
from backend.layer9_output.schemas.voice import AudioResult


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
