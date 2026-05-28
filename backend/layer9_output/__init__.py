# Layer 9 — Output Delivery & Interaction Orchestration
#
# Core question: How does Nova present its response?
#
# This layer translates everything computed by Layers 1-8 into the actual user experience:
# timing, tone, pacing, formatting, voice, and all micro-interactions.
#
# Central insight: Output is communication, not transcription.
# The SAME message lands completely differently depending on:
#   - Arrival timing (instant vs. 2-second pause)
#   - Format (paragraph vs. line breaks)
#   - Register (formal vs. casual)
#   - Delivery (text vs. voice)
#   - Micro-interactions (thinking pauses, backchannels, self-edits)
#
# Getting this wrong collapses the human-likeness illusion immediately.
# A brilliant response formatted like a corporate memo is worse than a simpler response delivered thoughtfully.
#
# Main components:
#   - interaction_orchestrator.py: SC-1 — Assembles event sequence, drives streaming
#   - stream_typing_overlay.py: Intercepts token stream, injects per-mode delays
#   - thinking_pause.py: Pause duration = f(complexity, emotional_intensity, circadian)
#   - self_edit_simulator.py: Show-phrase → delete → resume sequence
#   - length_calibrator.py: Compute length target
#   - micro_interaction_engine.py: SC-2 — 6-type micro-interaction taxonomy
#   - format_adapter.py: SC-4 — Register, markdown, emoji decisions
#   - voice_synthesizer.py: SC-3 — SSML assembly + TTS dispatch
#   - user_format_profile.py: Per-user learned format preferences
#   - tts_backends/: Swappable TTS implementations
#   - schemas.py: OrchestratedOutput, TypingEvent, FormatSpec, MicroInteractionPlan
#
# Contract: Layer 9 receives immutable response from Layer 4. Adds all delivery semantics.
