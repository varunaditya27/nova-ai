# Layer 9 TTS Backends
#
# Swappable text-to-speech implementations.
# All implement TTSBackend interface.
#
# Implemented backends:
#   - kokoro_backend.py: Kokoro TTS (OpenAI-compatible, runs locally in Docker)
#   - base_backend.py: Abstract interface
#
# Not built (no files yet, just documented future options): Google Cloud TTS, Azure Speech
# Services, ElevenLabs — swap in behind TTSBackend if a non-local voice provider is ever needed.
#
# Interface:
#   - synthesize(ssml_text: str) -> AudioBytes
#   - supports_ssml() -> bool
#   - get_available_voices() -> list[Voice]
#   - set_voice(voice_id: str) -> None
#   - health_check() -> bool
