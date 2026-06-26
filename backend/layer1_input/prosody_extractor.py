"""Layer 1 · Sub-Component 4 — Voice Prosody Extractor (architecture doc §6).

Spoken language carries emotional signal that transcription discards: hesitation, pitch
elevation, tremor, pace, volume dynamics. This component extracts those features when (and
only when) a voice note is received, behind an injectable on-device backend (SpeechBrain
ECAPA-TDNN, or a librosa rule-based fallback).

When no backend is configured — or extraction fails — it degrades to ``(None, None)`` so the
pipeline still emits a packet (§11). Raw audio is never persisted (§6.4): the backend reads
the in-RAM attachment buffer and the caller frees it after this pass.
"""

from __future__ import annotations

from typing import Optional, Protocol

from .schemas import (
    AttachmentPayload,
    ProsodyEmotionEstimate,
    ProsodyFeatures,
    VoiceCalibrationProfile,
)

# Calibration is only trusted as a deviation baseline above this confidence (§6.3).
CALIBRATION_MIN_CONFIDENCE = 0.5


class ProsodyBackend(Protocol):
    def extract(
        self, attachment: AttachmentPayload, calibration: Optional[VoiceCalibrationProfile]
    ) -> tuple[ProsodyFeatures, ProsodyEmotionEstimate]: ...


def compute_speech_rate_deviation(
    speech_rate: float, calibration: Optional[VoiceCalibrationProfile]
) -> float:
    """Speech rate as a signed deviation from the user's calibrated baseline (§6.3).

    Returns 0.0 until calibration is confident (5+ samples, confidence > 0.5); before then
    population norms are used downstream with lower weight, so the deviation is left neutral.
    """
    if (
        calibration is None
        or calibration.calibration_confidence <= CALIBRATION_MIN_CONFIDENCE
        or calibration.baseline_speech_rate <= 0
    ):
        return 0.0
    return (speech_rate - calibration.baseline_speech_rate) / calibration.baseline_speech_rate


def extract_prosody(
    attachment: AttachmentPayload,
    backend: Optional[ProsodyBackend] = None,
    calibration: Optional[VoiceCalibrationProfile] = None,
) -> tuple[Optional[ProsodyFeatures], Optional[ProsodyEmotionEstimate]]:
    """Extract prosodic features and an emotion estimate from a voice attachment (§6.2).

    Degrades to ``(None, None)`` when no backend is available or extraction fails. On success,
    the calibrated speech-rate deviation is written back onto the returned features.
    """
    if backend is None:
        return None, None
    try:
        features, estimate = backend.extract(attachment, calibration)
    except Exception:  # noqa: BLE001 — extraction failure must never break the pipeline (§11)
        return None, None

    features.speech_rate_deviation = compute_speech_rate_deviation(
        features.speech_rate_words_per_min, calibration
    )
    return features, estimate
