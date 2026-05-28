# Layer 9 TTS Backends
#
# Swappable text-to-speech implementations.
# All implement TTSBackend interface.
#
# Implemented backends:
#   - kokoro_backend.py: Kokoro TTS (OpenAI-compatible, runs locally in Docker)
#   - base_backend.py: Abstract interface
#
# Future backends (stubs):
#   - google_tts_backend.py (Google Cloud TTS)
#   - azure_tts_backend.py (Azure Speech Services)
#   - elevenlabs_backend.py (ElevenLabs)
#
# Interface:
#   - synthesize(ssml_text: str) -> AudioBytes
#   - supports_ssml() -> bool
#   - get_available_voices() -> list[Voice]
#   - set_voice(voice_id: str) -> None
#   - health_check() -> bool
