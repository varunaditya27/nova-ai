# Layer 9, Sub-Component: Voice Synthesizer (SC-3)
#
# Responsibility: Generate SSML markup for voice output and dispatch to TTS backend.
#
# SSML directives:
#   - Rate: speech speed (slower for emotional moments, normal for casual, faster for upbeat)
#   - Pitch: voice pitch (lower for serious, higher for upbeat, neutral for normal)
#   - Emphasis: which words to stress
#   - Pause: breath points and pause durations
#   - Break: sentence/paragraph boundaries
#
# Main functions:
#   - assemble_ssml(response_text, context) -> SSMLDocument
#   - synthesize_to_audio(ssml_doc) -> AudioBytes
#   - stream_audio(ssml_doc) -> AsyncGenerator[AudioChunk]
#
# Integration:
#   - Called only if voice_mode = True for this session
#   - Dispatches to active TTS backend (e.g., Kokoro via kokoro_backend)
#   - Returns audio bytes or stream
#   - Falls back to text if TTS fails
#
# Design: SSML makes voice output sound intentional, not robotic.
# Prosody changes convey emotional meaning.
