# Layer 9, Sub-Component: Stream Typing Overlay
#
# Responsibility: Intercept token stream from LLM; apply per-mode delays between tokens.
#
# Modes and their typing speeds (char/sec, from config/layer9.yaml):
#   - casual_chat: 55 (fast, conversational)
#   - supportive: 38 (slower, thoughtful)
#   - analytical: 48 (medium, deliberate)
#   - celebratory: 62 (faster, energetic)
#   - crisis_support: 30 (slow, intentional, present)
#
# Implementation:
#   - Streams tokens from LLM
#   - Batches into ~5-character chunks (for responsiveness)
#   - Inserts delays between chunks based on mode
#   - Applies circadian adjustment (late night = slower; morning = normal)
#
# Main functions:
#   - apply_typing_overlay(token_stream, mode, circadian) -> AsyncGenerator[TypingEvent]
#   - compute_delay_per_token(mode, circadian_band) -> float
#
# Integration:
#   - Runs during response streaming
#   - Reads mode from conversation_orchestrator context
#   - Feeds output to interaction_orchestrator
#
# Design: Typing speed is NOT added latency—it's client-side visual pacing.
# Server sends full response; client renders with per-token delays.
