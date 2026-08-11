"""Layer 9 — Output Delivery & Interaction Orchestration.

The final mile: translates everything Layers 1–8 computed into the actual words, timing, format,
pacing, and voice the user experiences. Output is communication, not transcription — the same
message lands differently depending on arrival timing, format, register, and medium.

Four sub-components:

    SC-1  interaction_orchestrator.py  — Interaction Orchestrator: assembles the typed-event
          (stream_typing_overlay,        sequence (thinking pause → pre-response signals → typing
           thinking_pause,               stream with mid-stream self-edit → send)
           self_edit_simulator,
           length_calibrator)
          delivery.py                  — the Layer 9 engine entry point (`deliver` → Layer9Output),
                                          running SC-4 → SC-2 → SC-1 → SC-3 in sequence
    SC-2  micro_interaction_engine.py  — Micro-Interaction Engine: the six-type taxonomy
    SC-3  voice_synthesizer.py         — Voice & SSML Synthesizer (+ tts_backends/: Kokoro)
    SC-4  format_adapter.py            — Format Adapter (+ user_format_profile.py learning)

Design commitments (architecture doc §11):
- Delivery is not decoration — timing, pacing, format and voice are the medium meaning travels in.
- The Orchestrator makes no LLM calls; every SC-1/SC-4 decision is deterministic and policy-driven.
  All randomness is injected (`rng`) so behavior is reproducible and testable offline.
- Format follows relationship before content; emotional/crisis content is always pure prose.
- Crisis mode is a single hard override that suppresses micro-interactions, self-edits, voice
  features and structure, and forces plain prose.
- Every sub-step degrades rather than blocks: a failure yields plain delivery, never no response.

Reconciliation (as-built): the scaffold and config used char/sec typing speeds with mode names
(casual/supportive/analytical/celebratory); the authoritative doc (§3.2) uses per-mode token
delays in ms keyed to the doc's conversation modes — the doc model is implemented and the config
rewritten to match. The doc's six-type micro-interaction taxonomy (§4.2) is implemented in place
of the scaffold's alternative list. TTS uses the project's Kokoro backend (CLAUDE.md infra) on the
abstract `TTSBackend` interface; the HTTP transport and all LLMs/backends are injected callables.
"""

from backend.layer9_output import (
    format_adapter,
    interaction_orchestrator,
    length_calibrator,
    micro_interaction_engine,
    schemas,
    self_edit_simulator,
    stream_typing_overlay,
    thinking_pause,
    user_format_profile,
    voice_synthesizer,
)
from backend.layer9_output import delivery
from backend.layer9_output.delivery import deliver
from backend.layer9_output.format_adapter import compute_format_spec, enforce_format_spec
from backend.layer9_output.interaction_orchestrator import orchestrate_output
from backend.layer9_output.length_calibrator import compute_length_target
from backend.layer9_output.micro_interaction_engine import plan_micro_interactions
from backend.layer9_output.self_edit_simulator import plan_self_edit
from backend.layer9_output.stream_typing_overlay import StreamTypingOverlay
from backend.layer9_output.thinking_pause import (
    compute_thinking_pause,
    should_show_thinking_indicator,
)
from backend.layer9_output.tts_backends.base_backend import TTSBackend
from backend.layer9_output.tts_backends.kokoro_backend import KokoroBackend
from backend.layer9_output.user_format_profile import (
    classify_format_feedback,
    initialize_defaults,
    update_format_profile,
)
from backend.layer9_output.voice_synthesizer import generate_ssml, synthesize
from backend.layer9_output.schemas import (
    AudioResult,
    CodeFormat,
    EmojiPolicy,
    FormatSpec,
    Layer9Output,
    LengthPreference,
    MicroInteractionPlan,
    OrchestratedOutput,
    ProsodyParams,
    Register,
    SSMLDocument,
    SelfEditPlan,
    Structure,
    TypingEvent,
    TypingEventType,
    UserFormatProfile,
)

__all__ = [
    # modules
    "delivery", "format_adapter", "interaction_orchestrator", "length_calibrator",
    "micro_interaction_engine", "schemas", "self_edit_simulator", "stream_typing_overlay",
    "thinking_pause", "user_format_profile", "voice_synthesizer",
    # entry points
    "deliver", "orchestrate_output",
    # SC-4
    "compute_format_spec", "enforce_format_spec", "initialize_defaults", "update_format_profile",
    "classify_format_feedback",
    # SC-1
    "compute_length_target", "compute_thinking_pause", "should_show_thinking_indicator",
    "plan_self_edit", "StreamTypingOverlay",
    # SC-2
    "plan_micro_interactions",
    # SC-3
    "generate_ssml", "synthesize", "TTSBackend", "KokoroBackend",
    # schemas
    "AudioResult", "CodeFormat", "EmojiPolicy", "FormatSpec", "Layer9Output", "LengthPreference",
    "MicroInteractionPlan", "OrchestratedOutput", "ProsodyParams",
    "Register", "SSMLDocument", "SelfEditPlan", "Structure", "TypingEvent", "TypingEventType",
    "UserFormatProfile",
]
