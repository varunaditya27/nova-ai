"""Tests for Layer 1 SC-3 — Multimodal Normalizer (architecture doc §5).

Normalizes every non-text modality into a ``ModalityContext``. Heavy model calls (vision,
Whisper, Tika) sit behind injectable backends; deterministic modalities (reaction, location)
need no backend. All failure / no-backend paths degrade gracefully per §11.
"""

from backend.layer1_input import multimodal_normalizer as mm
from backend.layer1_input.schemas import (
    AttachmentPayload,
    AttachmentType,
    DocumentSummary,
    DocumentType,
    PrimaryModality,
)


# ── Fake backends (dependency injection — no internal mocking) ───────────────
class FakeImageBackend:
    def describe(self, attachment):
        return mm.ImageResult(
            semantic_description="A screenshot of a rejection email",
            ocr_text="We regret to inform you",
            emotional_register_hint="disappointing news",
            modality_flags=["screenshot"],
            image_type="screenshot",
        )


class FakeVoiceBackend:
    def __init__(self, confidence=0.95, language="en"):
        self.confidence = confidence
        self.language = language

    def transcribe(self, attachment):
        return mm.VoiceTranscript(
            transcript="I'm fine, really",
            language_detected=self.language,
            confidence=self.confidence,
        )


class FakeDocBackend:
    def extract(self, attachment):
        return DocumentSummary(
            document_type=DocumentType.PROFESSIONAL,
            title="Offer Letter",
            extracted_text="We are pleased to offer you the position...",
            key_dates=["2026-07-01"],
            key_entities=["Infosys"],
            estimated_emotional_significance=0.6,
        )


class ExplodingImageBackend:
    def describe(self, attachment):
        raise ValueError("corrupt image data")


def _img():
    return AttachmentPayload(attachment_type=AttachmentType.IMAGE, mime_type="image/png",
                             data=b"\x89PNG")


def _voice(**kw):
    return AttachmentPayload(attachment_type=AttachmentType.VOICE, mime_type="audio/ogg",
                             data=b"OggS")


# ── Text ─────────────────────────────────────────────────────────────────────
def test_text_only():
    ctx = mm.normalize(raw_text="hello there", attachments=[])
    assert ctx.primary_modality == PrimaryModality.TEXT
    assert ctx.text_content == "hello there"
    assert ctx.semantic_description is None


# ── Reaction (deterministic, no backend) ─────────────────────────────────────
def test_reaction_heart_maps_to_affection():
    att = AttachmentPayload(attachment_type=AttachmentType.REACTION, reaction_emoji="❤️")
    ctx = mm.normalize(raw_text=None, attachments=[att])
    assert ctx.primary_modality == PrimaryModality.REACTION
    assert "affection" in ctx.emotional_register_hint


def test_reaction_laugh_maps_to_amusement():
    att = AttachmentPayload(attachment_type=AttachmentType.REACTION, reaction_emoji="\U0001f602")
    ctx = mm.normalize(raw_text=None, attachments=[att])
    assert "amusement" in ctx.emotional_register_hint


# ── Location (deterministic, no backend) ─────────────────────────────────────
def test_location_with_place_name():
    att = AttachmentPayload(attachment_type=AttachmentType.LOCATION, latitude=12.9,
                            longitude=77.5, place_name="University campus")
    ctx = mm.normalize(raw_text=None, attachments=[att])
    assert ctx.primary_modality == PrimaryModality.LOCATION
    assert "University campus" in ctx.location_description


# ── Image ────────────────────────────────────────────────────────────────────
def test_image_with_backend():
    backends = mm.NormalizerBackends(image=FakeImageBackend())
    ctx = mm.normalize(raw_text=None, attachments=[_img()], backends=backends)
    assert ctx.primary_modality == PrimaryModality.IMAGE
    assert ctx.semantic_description == "A screenshot of a rejection email"
    assert ctx.ocr_text == "We regret to inform you"
    assert "screenshot" in ctx.modality_flags


def test_image_without_backend_degrades():
    ctx = mm.normalize(raw_text=None, attachments=[_img()])
    assert ctx.primary_modality == PrimaryModality.IMAGE_UNPROCESSED
    assert ctx.semantic_description == "[Image could not be processed]"


def test_image_backend_failure_degrades():
    backends = mm.NormalizerBackends(image=ExplodingImageBackend())
    ctx = mm.normalize(raw_text=None, attachments=[_img()], backends=backends)
    assert ctx.primary_modality == PrimaryModality.IMAGE_UNPROCESSED
    assert "could not be processed" in ctx.semantic_description


# ── Voice ────────────────────────────────────────────────────────────────────
def test_voice_with_backend_produces_transcript():
    backends = mm.NormalizerBackends(voice=FakeVoiceBackend())
    ctx = mm.normalize(raw_text=None, attachments=[_voice()], backends=backends)
    assert ctx.primary_modality == PrimaryModality.VOICE
    assert ctx.text_content == "I'm fine, really"
    assert ctx.language_detected == "en"
    assert ctx.raw_voice_available is False  # always False in the emitted context (§5.6)


def test_voice_low_confidence_degrades_to_untranscribed():
    backends = mm.NormalizerBackends(voice=FakeVoiceBackend(confidence=0.3))
    ctx = mm.normalize(raw_text=None, attachments=[_voice()], backends=backends)
    assert ctx.primary_modality == PrimaryModality.VOICE_UNTRANSCRIBED
    assert "low_confidence_transcription" in ctx.modality_flags


def test_voice_language_switch_detected():
    backends = mm.NormalizerBackends(voice=FakeVoiceBackend(language="hi"))
    ctx = mm.normalize(raw_text=None, attachments=[_voice()], backends=backends,
                       established_language="en")
    assert ctx.language_switch_detected is True


def test_voice_without_backend_degrades():
    ctx = mm.normalize(raw_text=None, attachments=[_voice()])
    assert ctx.primary_modality == PrimaryModality.VOICE_UNTRANSCRIBED


# ── Document ─────────────────────────────────────────────────────────────────
def test_document_with_backend():
    att = AttachmentPayload(attachment_type=AttachmentType.DOCUMENT,
                            mime_type="application/pdf", filename="offer.pdf")
    backends = mm.NormalizerBackends(document=FakeDocBackend())
    ctx = mm.normalize(raw_text=None, attachments=[att], backends=backends)
    assert ctx.primary_modality == PrimaryModality.DOCUMENT
    assert ctx.document_summary.title == "Offer Letter"
    assert ctx.text_content == "We are pleased to offer you the position..."


# ── Mixed (text + media) ─────────────────────────────────────────────────────
def test_text_plus_image_is_mixed():
    backends = mm.NormalizerBackends(image=FakeImageBackend())
    ctx = mm.normalize(raw_text="look at this", attachments=[_img()], backends=backends)
    assert ctx.primary_modality == PrimaryModality.MIXED
    assert ctx.text_content == "look at this"          # text prioritized for semantics
    assert ctx.semantic_description == "A screenshot of a rejection email"  # image for emotion


def test_reaction_map_returns_label_and_hint_for_unknown_emoji():
    label, hint = mm.map_reaction("\U0001f984")  # unicorn — not in the table
    assert label == "reaction_signal"
    assert hint  # still a non-empty generic hint
