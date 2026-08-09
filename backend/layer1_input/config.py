"""Layer 1 — config-driven thresholds (architecture doc; mirrors ``config/layer1.yaml``).

A single frozen snapshot of every tunable value Layer 1's sub-components read, built once from
the merged app config (``Layer1Config.from_dict``) and threaded through each function as an
optional ``cfg`` parameter. Every field's default matches the value that was hardcoded in each
module before this was wired, so calling any function with no ``cfg`` (as every existing unit
test does) reproduces prior behavior exactly — this makes the wiring purely additive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Layer1Config:
    # ── SC-1 Temporal Resolver ────────────────────────────────────────────────
    circadian_bands: dict = field(default_factory=lambda: {
        "late_night": (23, 3), "early_morning": (3, 6), "morning": (6, 12),
        "afternoon": (12, 17), "evening": (17, 21), "night": (21, 23),
    })
    circadian_mood_prior: dict = field(default_factory=lambda: {
        "late_night": 0.75, "early_morning": 0.80, "morning": 0.20,
        "afternoon": 0.25, "evening": 0.40, "night": 0.55,
    })
    personalized_prior_min_sessions: int = 20
    anomaly_min_sessions: int = 5
    session_gap_categories: dict = field(default_factory=lambda: {
        "same_session": 1800, "short_break": 14400, "same_day": 86400,
        "few_days": 259200, "week_or_two": 1209600, "long_absence": 7776000,
    })
    new_session_threshold_seconds: int = 1800
    atypical_band_frequency: float = 0.05
    long_gap_multiplier: float = 2.5
    rapid_return_ratio: float = 0.10

    # ── SC-2 Implicit Signal Extractor ────────────────────────────────────────
    latency_thresholds_ms: dict = field(default_factory=lambda: {
        "reactive": 3000, "quick": 15000, "considered": 60000,
        "reflective": 300000, "delayed": 1200000,
    })
    latency_intensity_weights: dict = field(default_factory=lambda: {
        "reactive": 0.6, "quick": 0.2, "considered": 0.0,
        "reflective": 0.1, "delayed": 0.2, "break": 0.0,
    })
    intensity_latency_scale: float = 0.25
    intensity_deletion_scale: float = 0.20
    intensity_length_long_scale: float = 0.25
    intensity_length_withdrawal: float = 0.20
    intensity_initiation_cold: float = 0.10

    # ── SC-3 Multimodal Normalizer ────────────────────────────────────────────
    min_transcription_confidence: float = 0.5

    # ── SC-4 Voice Prosody Extractor ──────────────────────────────────────────
    calibration_min_confidence: float = 0.5

    # ── SC-5 Assembler ────────────────────────────────────────────────────────
    low_vulnerability_prior: float = 0.30
    high_implicit_intensity: float = 0.60
    prosody_min_confidence: float = 0.40
    distress_valence_threshold: float = -0.30
    composite_weights: dict = field(default_factory=lambda: {
        "circadian": 0.15, "implicit": 0.35, "prosody": 0.50,
    })
    anomaly_signal_bonus: float = 0.08

    # ── Pending threads (§3.5) ────────────────────────────────────────────────
    max_surfaced_threads: int = 2
    importance_tier_score: dict = field(default_factory=lambda: {
        "critical": 1.0, "high": 0.75, "medium": 0.50, "low": 0.25,
    })

    @classmethod
    def from_dict(cls, app_config: Optional[dict]) -> "Layer1Config":
        """Build from the merged app config's ``config['layer1']`` section. Any key missing
        from the YAML (or the whole section, or ``app_config`` itself) falls back to the field
        default above — i.e. today's hardcoded value."""
        raw = ((app_config or {}).get("layer1") or {})
        d = cls()  # field defaults
        anomaly = raw.get("anomaly", {})
        weights = raw.get("implicit_intensity_weights", {})
        asm = raw.get("assembler", {})
        threads = raw.get("threads", {})
        bands = {name: (b["start_hour"], b["end_hour"])
                 for name, b in raw.get("circadian_bands", {}).items()} or None
        return cls(
            circadian_bands=bands or d.circadian_bands,
            circadian_mood_prior={**d.circadian_mood_prior, **raw.get("circadian_mood_prior", {})},
            personalized_prior_min_sessions=raw.get(
                "personalized_prior_min_sessions", d.personalized_prior_min_sessions),
            anomaly_min_sessions=anomaly.get("min_sessions", d.anomaly_min_sessions),
            session_gap_categories={**d.session_gap_categories,
                                    **raw.get("session_gap_categories", {})},
            new_session_threshold_seconds=raw.get(
                "new_session_threshold_seconds", d.new_session_threshold_seconds),
            atypical_band_frequency=anomaly.get("atypical_band_frequency", d.atypical_band_frequency),
            long_gap_multiplier=anomaly.get("long_gap_multiplier", d.long_gap_multiplier),
            rapid_return_ratio=anomaly.get("rapid_return_ratio", d.rapid_return_ratio),
            latency_thresholds_ms={**d.latency_thresholds_ms, **raw.get("latency_thresholds_ms", {})},
            latency_intensity_weights={**d.latency_intensity_weights, **weights.get("latency", {})},
            intensity_latency_scale=weights.get("latency_scale", d.intensity_latency_scale),
            intensity_deletion_scale=weights.get("deletion_scale", d.intensity_deletion_scale),
            intensity_length_long_scale=weights.get(
                "length_long_scale", d.intensity_length_long_scale),
            intensity_length_withdrawal=weights.get(
                "length_withdrawal", d.intensity_length_withdrawal),
            intensity_initiation_cold=weights.get("initiation_cold", d.intensity_initiation_cold),
            min_transcription_confidence=raw.get("multimodal", {}).get(
                "min_transcription_confidence", d.min_transcription_confidence),
            calibration_min_confidence=raw.get("prosody", {}).get(
                "calibration_min_confidence", d.calibration_min_confidence),
            low_vulnerability_prior=asm.get("low_vulnerability_prior", d.low_vulnerability_prior),
            high_implicit_intensity=asm.get("high_implicit_intensity", d.high_implicit_intensity),
            prosody_min_confidence=asm.get("prosody_min_confidence", d.prosody_min_confidence),
            distress_valence_threshold=asm.get(
                "distress_valence_threshold", d.distress_valence_threshold),
            composite_weights={**d.composite_weights, **asm.get("composite_weights", {})},
            anomaly_signal_bonus=asm.get("anomaly_signal_bonus", d.anomaly_signal_bonus),
            max_surfaced_threads=threads.get("max_surfaced_per_session", d.max_surfaced_threads),
            importance_tier_score={**d.importance_tier_score,
                                   **threads.get("importance_tier_score", {})},
        )
