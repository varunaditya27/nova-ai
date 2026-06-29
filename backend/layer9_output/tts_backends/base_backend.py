"""Base TTS backend interface (architecture doc §5.7).

Abstract base for all TTS providers so engine selection is transparent to the rest of Layer 9.
Subclasses implement ``synthesize``; the base provides safe defaults for capability/health hooks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.layer9_output.schemas import AudioResult


class TTSBackend(ABC):
    """Uniform interface the Voice Synthesizer calls every TTS provider through."""

    @abstractmethod
    def synthesize(self, ssml_text: str, voice_id: Optional[str] = None) -> AudioResult:
        """Render ``ssml_text`` to audio, returning an AudioResult (ok flag + bytes/error)."""

    def supports_ssml(self) -> bool:
        return True

    def get_available_voices(self) -> list:
        return []

    def set_voice(self, voice_id: str) -> None:
        self.default_voice = voice_id

    def health_check(self) -> bool:
        return True

    def authenticate(self) -> bool:
        return True
