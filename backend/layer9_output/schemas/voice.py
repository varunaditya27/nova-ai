"""Voice & SSML Synthesizer contracts — SC-3 (§5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProsodyParams:
    rate: str = "medium"
    pitch: str = "+0"


@dataclass
class SSMLDocument:
    ssml: str = ""
    prosody: Optional[ProsodyParams] = None
    fillers_included: bool = False


@dataclass
class AudioResult:
    audio_bytes: bytes = b""
    content_type: str = "audio/mpeg"
    ok: bool = True
    error: Optional[str] = None


@dataclass
class TranscriptResult:
    transcript: str = ""
    confidence: float = 0.0
    language: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
