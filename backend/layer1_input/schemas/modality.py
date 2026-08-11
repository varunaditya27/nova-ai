"""SC-3/SC-4 modality + prosody sub-component types (architecture doc §5, §6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import DocumentType, ProsodyDominantSignal, PrimaryModality


@dataclass
class DocumentSummary:
    """Normalized document representation (architecture doc §5.5)."""

    document_type: DocumentType = DocumentType.UNKNOWN
    title: Optional[str] = None
    extracted_text: str = ""                       # full text, up to 10,000 chars
    key_dates: list[str] = field(default_factory=list)
    key_entities: list[str] = field(default_factory=list)
    estimated_emotional_significance: float = 0.0  # 0–1


@dataclass
class ModalityContext:
    """Normalized representation of any non-text input (architecture doc §5.6)."""

    primary_modality: PrimaryModality = PrimaryModality.TEXT
    text_content: Optional[str] = None
    semantic_description: Optional[str] = None
    ocr_text: Optional[str] = None
    document_summary: Optional[DocumentSummary] = None
    location_description: Optional[str] = None
    emotional_register_hint: Optional[str] = None
    modality_flags: list[str] = field(default_factory=list)
    raw_voice_available: bool = False              # True only during SC-4; False in final packet
    language_detected: Optional[str] = None        # ISO 639-1
    language_switch_detected: bool = False


@dataclass
class ProsodyFeatures:
    """Raw prosodic measurements (architecture doc §6.2)."""

    speech_rate_words_per_min: float = 0.0
    speech_rate_deviation: float = 0.0
    pitch_mean_hz: float = 0.0
    pitch_variance: float = 0.0
    energy_mean_db: float = 0.0
    energy_variance: float = 0.0
    pause_frequency: float = 0.0
    pause_mean_duration_ms: float = 0.0
    voice_tremor_detected: bool = False
    vocal_fry_detected: bool = False
    breathiness_score: float = 0.0                 # 0–1


@dataclass
class ProsodyEmotionEstimate:
    """Derived prosodic emotion estimate (architecture doc §6.2)."""

    valence: float = 0.0       # –1 (negative) … +1 (positive)
    arousal: float = 0.0       # 0 (calm) … 1 (activated)
    confidence: float = 0.0    # 0–1; lower for noisy audio
    dominant_signal: Optional[ProsodyDominantSignal] = None


@dataclass
class VoiceCalibrationProfile:
    """Per-user voice baseline, built after 5+ voice inputs (architecture doc §6.3)."""

    baseline_speech_rate: float = 0.0
    baseline_pitch_mean: float = 0.0
    baseline_pitch_variance: float = 0.0
    baseline_energy_mean: float = 0.0
    samples_used: int = 0
    calibration_confidence: float = 0.0            # 0–1; <0.5 until 10+ samples
