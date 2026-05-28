# Test: Kokoro TTS Backend
#
# Tests:
#   - Connect to Kokoro TTS backend (Docker container on localhost:8880)
#   - Send OpenAI-compatible request
#   - Receive audio stream
#   - Handle connection errors
#   - Support SSML markup (rate, pitch, emphasis, pause, break)
#
# Fixtures: mock_tts_docker_container
