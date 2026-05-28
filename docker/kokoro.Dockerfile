# Kokoro TTS Docker Container
#
# Purpose: Serve text-to-speech via OpenAI-compatible API
#
# Image: kokoro-tts:latest
# Port: 8880
# Protocol: OpenAI-compatible REST API
#
# Endpoints:
#   POST /v1/audio/speech
#     - Input: { model, input, voice, response_format, speed }
#     - Output: audio stream (mp3/opus/aac/flac)
#
# Configuration:
#   - KOKORO_MODEL: voice model (default: kokoro)
#   - KOKORO_PORT: API port (default: 8880)
#
# Build:
#   docker build -f docker/kokoro.Dockerfile -t kokoro-tts:latest .
#
# Run (standalone):
#   docker run -p 8880:8880 kokoro-tts:latest
#
# Integration:
#   Used by Layer 9 (voice_synthesizer.py)
#   Connected via docker-compose or localhost:8880
