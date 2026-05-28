# Kokoro TTS Backend
#
# Integrates with Kokoro TTS service running in Docker on localhost:8880.
#
# Interface: OpenAI-compatible /v1/audio/speech endpoint.
# Input: SSML text + voice_id + speech_rate
# Output: Audio bytes (MP3 or WAV)
#
# Main functions:
#   - synthesize(ssml_text, voice_id, speech_rate) -> AudioBytes
#   - stream_synthesize(ssml_text, ...) -> AsyncGenerator[AudioChunk]
#   - health_check() -> bool
#
# Integration:
#   - Called by voice_synthesizer.py when TTS is enabled
#   - Requires docker-compose.yml to have Kokoro service running
#   - Falls back to text if service unavailable
#
# Configuration: Kokoro endpoint, available voices, and default speech rate
# are read from config/layer9.yaml or environment variables.
