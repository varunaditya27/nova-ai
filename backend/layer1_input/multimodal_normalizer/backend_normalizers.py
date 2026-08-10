"""Modalities that call an injectable model backend (§5.3–§5.5): image, voice, document.

Every backend failure or missing-backend path degrades gracefully and still returns a
valid ``ModalityContext`` (§11 "always emit").
"""

from __future__ import annotations

from typing import Optional

from ..config import Layer1Config
from ..schemas import AttachmentPayload, DocumentSummary, ModalityContext, PrimaryModality
from .types import DocumentBackend, ImageBackend, VoiceBackend

_DEFAULT = Layer1Config()


def normalize_image(att: AttachmentPayload, backend: Optional[ImageBackend]) -> ModalityContext:
    if backend is None:
        return ModalityContext(
            primary_modality=PrimaryModality.IMAGE_UNPROCESSED,
            semantic_description="[Image could not be processed]",
        )
    try:
        result = backend.describe(att)
    except Exception:  # noqa: BLE001 — any backend failure degrades, never raises (§11)
        return ModalityContext(
            primary_modality=PrimaryModality.IMAGE_UNPROCESSED,
            semantic_description="[Image could not be processed]",
        )
    return ModalityContext(
        primary_modality=PrimaryModality.IMAGE,
        semantic_description=result.semantic_description,
        ocr_text=result.ocr_text,
        emotional_register_hint=result.emotional_register_hint,
        modality_flags=list(result.modality_flags),
    )


def normalize_voice(
    att: AttachmentPayload,
    backend: Optional[VoiceBackend],
    established_language: Optional[str],
    cfg: Optional[Layer1Config] = None,
) -> ModalityContext:
    if backend is None:
        return ModalityContext(
            primary_modality=PrimaryModality.VOICE_UNTRANSCRIBED,
            semantic_description="[Voice note could not be transcribed]",
        )
    try:
        result = backend.transcribe(att)
    except Exception:  # noqa: BLE001
        return ModalityContext(
            primary_modality=PrimaryModality.VOICE_UNTRANSCRIBED,
            semantic_description="[Voice note could not be transcribed]",
        )

    switched = (
        established_language is not None
        and result.language_detected is not None
        and result.language_detected != established_language
    )

    if result.confidence < (cfg or _DEFAULT).min_transcription_confidence:
        # Keep the low-confidence transcript but flag it; SC-4 is skipped downstream (§11).
        return ModalityContext(
            primary_modality=PrimaryModality.VOICE_UNTRANSCRIBED,
            text_content=result.transcript,
            modality_flags=["low_confidence_transcription"],
            language_detected=result.language_detected,
            language_switch_detected=switched,
        )

    return ModalityContext(
        primary_modality=PrimaryModality.VOICE,
        text_content=result.transcript,
        language_detected=result.language_detected,
        language_switch_detected=switched,
        raw_voice_available=False,  # raw audio lives only in the SC-4 buffer, never here
    )


def normalize_document(
    att: AttachmentPayload, backend: Optional[DocumentBackend]
) -> ModalityContext:
    if backend is None:
        return ModalityContext(
            primary_modality=PrimaryModality.DOCUMENT,
            semantic_description=f"[Document attached: {att.filename or 'unknown'}]",
            document_summary=DocumentSummary(),
        )
    try:
        summary = backend.extract(att)
    except Exception:  # noqa: BLE001
        return ModalityContext(
            primary_modality=PrimaryModality.DOCUMENT,
            semantic_description=f"[Document could not be extracted: {att.filename or 'unknown'}]",
            document_summary=DocumentSummary(),
        )
    return ModalityContext(
        primary_modality=PrimaryModality.DOCUMENT,
        text_content=summary.extracted_text or None,
        semantic_description=summary.title,
        document_summary=summary,
    )
