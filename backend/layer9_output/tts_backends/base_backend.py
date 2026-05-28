# Base TTS Backend Interface
#
# Abstract base class for all TTS implementations.
# Enforces consistent interface across all TTS providers.
#
# Methods:
#   - synthesize(ssml_text: str, voice_id: str = None) -> AudioBytes
#   - stream_synthesize(ssml_text: str, voice_id: str = None) -> AsyncGenerator[AudioChunk]
#   - supports_ssml() -> bool
#   - get_available_voices() -> list[Voice]
#   - set_voice(voice_id: str) -> None
#   - health_check() -> bool
#   - authenticate() -> bool (if auth required)
#
# All subclasses must implement. Allows easy provider swaps.
