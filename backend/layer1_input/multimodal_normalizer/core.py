"""Layer 1 · Sub-Component 3 — Multimodal Normalizer entry point (§5).

The sole entry point for non-text input. Every modality is normalized to a text-compatible
``ModalityContext`` so no downstream agent ever touches raw binary data.
"""

from __future__ import annotations

from typing import Optional

from ..config import Layer1Config
from ..schemas import AttachmentPayload, AttachmentType, ModalityContext, PrimaryModality
from .backend_normalizers import normalize_document, normalize_image, normalize_voice
from .deterministic import normalize_location, normalize_reaction
from .types import NormalizerBackends


def _normalize_one(
    att: AttachmentPayload, backends: NormalizerBackends, established_language: Optional[str],
    cfg: Optional[Layer1Config] = None,
) -> ModalityContext:
    if att.attachment_type == AttachmentType.IMAGE:
        return normalize_image(att, backends.image)
    if att.attachment_type == AttachmentType.VOICE:
        return normalize_voice(att, backends.voice, established_language, cfg)
    if att.attachment_type == AttachmentType.DOCUMENT:
        return normalize_document(att, backends.document)
    if att.attachment_type == AttachmentType.REACTION:
        return normalize_reaction(att)
    if att.attachment_type == AttachmentType.LOCATION:
        return normalize_location(att)
    if att.attachment_type == AttachmentType.VIDEO:
        # Video reuses the image backend on sampled keyframes (§5.2); degrade if absent.
        if backends.image is None:
            return ModalityContext(
                primary_modality=PrimaryModality.VIDEO,
                semantic_description="[Video could not be processed]",
            )
        ctx = normalize_image(att, backends.image)
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
