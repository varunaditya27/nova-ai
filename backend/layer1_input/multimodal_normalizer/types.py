"""Backend result types and injectable Protocols for the Multimodal Normalizer (§5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from ..schemas import AttachmentPayload, DocumentSummary


@dataclass
class ImageResult:
    semantic_description: str
    ocr_text: Optional[str] = None
    emotional_register_hint: Optional[str] = None
    modality_flags: list[str] = field(default_factory=list)
    image_type: Optional[str] = None


@dataclass
class VoiceTranscript:
    transcript: str
    language_detected: Optional[str] = None
    confidence: float = 1.0


class ImageBackend(Protocol):
    def describe(self, attachment: AttachmentPayload) -> ImageResult: ...


class VoiceBackend(Protocol):
    def transcribe(self, attachment: AttachmentPayload) -> VoiceTranscript: ...


class DocumentBackend(Protocol):
    def extract(self, attachment: AttachmentPayload) -> DocumentSummary: ...


@dataclass
class NormalizerBackends:
    """Injectable model backends. ``None`` for any modality → graceful degraded output."""

    image: Optional[ImageBackend] = None
    voice: Optional[VoiceBackend] = None
    document: Optional[DocumentBackend] = None
