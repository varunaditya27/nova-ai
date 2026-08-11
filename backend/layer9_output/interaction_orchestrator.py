"""SC-1 — Interaction Orchestrator event assembly (architecture doc §3.5).

``orchestrate_output`` turns the final response text plus a FormatSpec, a MicroInteractionPlan,
a thinking pause, and an optional self-edit plan into an ordered list of typed events the UI
replays (thinking pause → pre-response signals → typing stream with mid-stream self-edit →
send). Pure orchestration — no LLM calls.

The Layer 9 entry point (``deliver``, which runs SC-4 → SC-2 → SC-1 → SC-3) lives in
``delivery.py``.
"""

from __future__ import annotations

import random as _random
import re
from typing import Optional

from backend.layer9_output.schemas import (
    MicroInteractionPlan,
    OrchestratedOutput,
    SelfEditPlan,
    TypingEvent,
    TypingEventType,
)
from backend.layer9_output.stream_typing_overlay import StreamTypingOverlay


def _safe(fn, fallback):
    """Run fn(); on any failure return fallback (§9 — degrade, never block delivery)."""
    try:
        return fn()
    except Exception:
        return fallback


def _tokenize(text: str) -> list[str]:
    """Split into word-ish tokens preserving trailing whitespace."""
    return re.findall(r"\S+\s*", text) or ([text] if text else [])


def orchestrate_output(
    final_response_text: str,
    conversation_mode: str,
    circadian_band: str = "afternoon",
    format_spec=None,
    micro_plan: Optional[MicroInteractionPlan] = None,
    thinking_pause_ms: int = 0,
    self_edit_plan: Optional[SelfEditPlan] = None,
    voice_ssml: Optional[str] = None,
    rng=_random,
) -> OrchestratedOutput:
    """Assemble the ordered event sequence for the UI (architecture doc §3.5)."""
    micro_plan = micro_plan or MicroInteractionPlan()
    overlay = StreamTypingOverlay()
    events: list[TypingEvent] = []

    # A closing signal replaces the response entirely (§4.2 Type 6).
    if micro_plan.closing_signal:
        final_text = micro_plan.closing_signal
    elif micro_plan.transition_phrase:
        final_text = f"{micro_plan.transition_phrase} {final_response_text}"
    else:
        final_text = final_response_text

    # 1) Thinking pause.
    if thinking_pause_ms > 0:
        events.append(TypingEvent(event_type=TypingEventType.THINKING_PAUSE.value,
                                  duration_ms=thinking_pause_ms, delay_before_ms=thinking_pause_ms))

    # 2) Pre-response micro-signals (acknowledgment, then emotional prefix).
    backchannel_text = micro_plan.acknowledgment
    if micro_plan.acknowledgment:
        events.append(TypingEvent(event_type=TypingEventType.BACKCHANNEL.value,
                                  text=micro_plan.acknowledgment, delay_before_ms=600))
    if micro_plan.emotional_prefix:
        events.append(TypingEvent(event_type=TypingEventType.BACKCHANNEL.value,
                                  text=micro_plan.emotional_prefix, delay_before_ms=500))

    # 3) Typing stream with optional mid-stream self-edit.
    events.append(TypingEvent(event_type=TypingEventType.START_TYPING.value))
    tokens = _tokenize(final_text)
    edit_fired = False
    chars_emitted = 0
    prev_token = ""
    for token in tokens:
        if (self_edit_plan and not edit_fired
                and chars_emitted >= self_edit_plan.insert_after_chars):
            events.append(TypingEvent(event_type=TypingEventType.SHOW_PHRASE.value,
                                      phrase=self_edit_plan.phrase_to_show_then_delete))
            events.append(TypingEvent(event_type=TypingEventType.DELETE_PHRASE.value,
                                      phrase=self_edit_plan.phrase_to_show_then_delete,
                                      delay_before_ms=self_edit_plan.deletion_pause_ms))
            events.append(TypingEvent(event_type=TypingEventType.RESUME_TYPING.value,
                                      delay_before_ms=self_edit_plan.resume_pause_ms))
            edit_fired = True
        events.extend(overlay.emit_token(token, prev_token, conversation_mode, circadian_band, rng))
        chars_emitted += len(token)
        prev_token = token

    # 4) Final send.
    events.append(TypingEvent(event_type=TypingEventType.SEND_MESSAGE.value, text=final_text))

    return OrchestratedOutput(
        events=events, final_message_text=final_text, backchannel_text=backchannel_text,
        format_spec=format_spec, voice_ssml=voice_ssml,
        estimated_render_duration_ms=sum(e.delay_before_ms or 0 for e in events))
