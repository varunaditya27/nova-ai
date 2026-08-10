"""Base STT backend interface, sibling to tts_backends/base_backend.py.

Abstract base for all speech-to-text providers so engine selection is transparent to callers.
Subclasses implement ``transcribe``; the base provides a safe default health-check.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.layer9_output.schemas import TranscriptResult


class STTBackend(ABC):
    """Uniform interface the dictation endpoint calls every STT provider through."""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> TranscriptResult:
        """Transcribe ``audio_bytes`` to text, returning a TranscriptResult (ok flag + text/error)."""

    def health_check(self) -> bool:
        return True
