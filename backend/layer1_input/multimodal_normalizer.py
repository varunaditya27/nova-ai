"""Layer 1 · Sub-Component 3 — Multimodal Normalizer (architecture doc §5).

The sole entry point for non-text input. Every modality is normalized to a text-compatible
``ModalityContext`` so no downstream agent ever touches raw binary data.

Heavy model calls — vision (LLaVA / GPT-4o), transcription (Whisper.cpp), document extraction
(Apache Tika) — sit behind injectable backend Protocols. Deterministic modalities (reaction,
location) need no backend. Every failure or missing-backend path degrades gracefully and still
returns a valid context (§11 "always emit").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from .config import Layer1Config
from .schemas import (
    AttachmentPayload,
    AttachmentType,
    DocumentSummary,
    ModalityContext,
    PrimaryModality,
)

# Fallback when no ``cfg`` is supplied (every existing unit test). Whisper transcripts below
# this confidence degrade to VOICE_UNTRANSCRIBED (§11).
_DEFAULT = Layer1Config()

# Reaction emoji → (emotion label, register hint) (§5.2).
REACTION_EMOJI_MAP: dict[str, tuple[str, str]] = {
    "❤️": ("affection_signal", "affection / warmth"),
    "\U0001f602": ("amusement_signal", "amusement / laughter"),   # 😂
    "\U0001f44d": ("approval_signal", "approval / agreement"),    # 👍
    "\U0001f622": ("sadness_signal", "sadness / sympathy"),       # 😢
    "\U0001f621": ("anger_signal", "anger / frustration"),        # 😡
    "\U0001f64f": ("gratitude_signal", "gratitude / pleading"),   # 🙏
    "\U0001f525": ("excitement_signal", "excitement / emphasis"),  # 🔥
}


# ── Backend results & protocols ──────────────────────────────────────────────
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


def map_reaction(emoji: str) -> tuple[str, str]:
    """Map a reaction emoji to (emotion_label, register_hint) (§5.2)."""
    return REACTION_EMOJI_MAP.get(emoji, ("reaction_signal", "an emotional reaction"))


# ── Per-modality normalizers ─────────────────────────────────────────────────
def _normalize_image(att: AttachmentPayload, backend: Optional[ImageBackend]) -> ModalityContext:
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


def _normalize_voice(
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


def _normalize_document(
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


def _normalize_reaction(att: AttachmentPayload) -> ModalityContext:
    label, hint = map_reaction(att.reaction_emoji or "")
    return ModalityContext(
        primary_modality=PrimaryModality.REACTION,
        semantic_description=f"User reacted with {att.reaction_emoji or 'a reaction'}",
        emotional_register_hint=hint,
        modality_flags=[label],
    )


def _normalize_location(att: AttachmentPayload) -> ModalityContext:
    place = att.place_name or "an unspecified location"
    flags = ["location"]
    if att.place_name is None:
        flags.append("new_location")
    return ModalityContext(
        primary_modality=PrimaryModality.LOCATION,
        location_description=f"Near {place}",
        modality_flags=flags,
    )


def _normalize_one(
    att: AttachmentPayload, backends: NormalizerBackends, established_language: Optional[str],
    cfg: Optional[Layer1Config] = None,
) -> ModalityContext:
    if att.attachment_type == AttachmentType.IMAGE:
        return _normalize_image(att, backends.image)
    if att.attachment_type == AttachmentType.VOICE:
        return _normalize_voice(att, backends.voice, established_language, cfg)
    if att.attachment_type == AttachmentType.DOCUMENT:
        return _normalize_document(att, backends.document)
    if att.attachment_type == AttachmentType.REACTION:
        return _normalize_reaction(att)
    if att.attachment_type == AttachmentType.LOCATION:
        return _normalize_location(att)
    if att.attachment_type == AttachmentType.VIDEO:
        # Video reuses the image backend on sampled keyframes (§5.2); degrade if absent.
        if backends.image is None:
            return ModalityContext(
                primary_modality=PrimaryModality.VIDEO,
                semantic_description="[Video could not be processed]",
            )
        ctx = _normalize_image(att, backends.image)
        ctx.primary_modality = PrimaryModality.VIDEO
        return ctx
    # Generic file: metadata only (§5.2).
    return ModalityContext(
        primary_modality=PrimaryModality.DOCUMENT,
        semantic_description=f"[File attached: {att.filename or 'unknown'} "
        f"({att.mime_type or 'unknown type'})]",
    )


def normalize(
    raw_text: Optional[str],
    attachments: list[AttachmentPayload],
    backends: Optional[NormalizerBackends] = None,
    established_language: Optional[str] = None,
    cfg: Optional[Layer1Config] = None,
) -> ModalityContext:
    """Normalize a message + attachments into a single ``ModalityContext`` (§5.6).

    * No attachments → plain ``TEXT``.
    * One attachment, no text → that attachment's modality.
    * Text plus any media, or multiple attachments → ``MIXED`` (text carries semantic
      content; media carries emotional context, per §7.2 conflict rule 4).
    """
    backends = backends or NormalizerBackends()
    has_text = bool(raw_text and raw_text.strip())

    if not attachments:
        return ModalityContext(primary_modality=PrimaryModality.TEXT, text_content=raw_text)

    contexts = [_normalize_one(att, backends, established_language, cfg) for att in attachments]
    primary_media = contexts[0]

    is_mixed = has_text or len(contexts) > 1
    if not is_mixed:
        # Single media attachment, no accompanying text.
        return primary_media

    # MIXED: prioritize text for semantics, carry the first media's emotional/semantic hints.
    merged_flags: list[str] = []
    for ctx in contexts:
        merged_flags.extend(ctx.modality_flags)

    return ModalityContext(
        primary_modality=PrimaryModality.MIXED,
        text_content=raw_text if has_text else primary_media.text_content,
        semantic_description=primary_media.semantic_description,
        ocr_text=primary_media.ocr_text,
        document_summary=primary_media.document_summary,
        location_description=primary_media.location_description,
        emotional_register_hint=primary_media.emotional_register_hint,
        modality_flags=merged_flags,
        language_detected=primary_media.language_detected,
        language_switch_detected=primary_media.language_switch_detected,
    )
