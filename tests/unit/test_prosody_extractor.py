"""Tests for Layer 1 SC-4 — Voice Prosody Extractor (architecture doc §6).

Runs only on voice input, behind an injectable backend (SpeechBrain / librosa). Without a
backend it degrades to ``(None, None)`` so the pipeline still emits a packet. Prosody feature
interpretation uses deviation from the per-user calibrated baseline once confident (§6.3).
"""

from backend.layer1_input import prosody_extractor as pe
from backend.layer1_input.schemas import (
    AttachmentPayload,
    AttachmentType,
    ProsodyDominantSignal,
    ProsodyEmotionEstimate,
    ProsodyFeatures,
    VoiceCalibrationProfile,
)


class FakeProsodyBackend:
    def extract(self, attachment, calibration):
        features = ProsodyFeatures(
            speech_rate_words_per_min=180.0,
            pitch_mean_hz=220.0,
            pitch_variance=80.0,
            energy_mean_db=-12.0,
            voice_tremor_detected=True,
            breathiness_score=0.7,
        )
        estimate = ProsodyEmotionEstimate(
            valence=-0.6, arousal=0.8, confidence=0.85,
            dominant_signal=ProsodyDominantSignal.DISTRESSED,
        )
        return features, estimate


class ExplodingProsodyBackend:
    def extract(self, attachment, calibration):
        raise RuntimeError("audio decode failed")


def _voice():
    return AttachmentPayload(attachment_type=AttachmentType.VOICE, mime_type="audio/ogg",
                             data=b"OggS")


def test_no_backend_returns_none():
    features, estimate = pe.extract_prosody(_voice(), backend=None)
    assert features is None
    assert estimate is None


def test_backend_failure_degrades_to_none():
    features, estimate = pe.extract_prosody(_voice(), backend=ExplodingProsodyBackend())
    assert features is None and estimate is None


def test_backend_returns_features_and_estimate():
    features, estimate = pe.extract_prosody(_voice(), backend=FakeProsodyBackend())
    assert features.voice_tremor_detected is True
    assert estimate.dominant_signal == ProsodyDominantSignal.DISTRESSED
    assert estimate.valence == -0.6


def test_speech_rate_deviation_uses_calibration_when_confident():
    calib = VoiceCalibrationProfile(baseline_speech_rate=120.0, calibration_confidence=0.8)
    # (180 - 120) / 120 = 0.5
    assert pe.compute_speech_rate_deviation(180.0, calib) == 0.5


def test_speech_rate_deviation_zero_when_calibration_unconfident():
    calib = VoiceCalibrationProfile(baseline_speech_rate=120.0, calibration_confidence=0.3)
    assert pe.compute_speech_rate_deviation(180.0, calib) == 0.0


def test_speech_rate_deviation_zero_without_calibration():
    assert pe.compute_speech_rate_deviation(180.0, None) == 0.0


def test_extract_applies_calibration_deviation_to_features():
    calib = VoiceCalibrationProfile(baseline_speech_rate=120.0, calibration_confidence=0.8)
    features, _ = pe.extract_prosody(_voice(), backend=FakeProsodyBackend(), calibration=calib)
    assert features.speech_rate_deviation == 0.5
