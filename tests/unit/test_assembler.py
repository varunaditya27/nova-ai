"""Tests for Layer 1 SC-5 — Input Perception Assembler (architecture doc §7).

The Assembler collects SC-1…SC-4 outputs, resolves signal conflicts (§7.2), computes the
composite emotional prior (§7.4), and emits the single ``InputPerceptionPacket``.
"""

from datetime import datetime, time
from uuid import uuid4

import pytest

from backend.layer1_input import assembler as asm
from backend.layer1_input.schemas import (
    InputPerceptionPacket,
    ModalityContext,
    PrimaryModality,
    ProsodyDominantSignal,
    ProsodyEmotionEstimate,
)


# ── Composite emotional prior (§7.4, verbatim formula) ───────────────────────
def test_composite_prior_circadian_and_implicit_only():
    prior, conf = asm.compute_composite_prior(
        circadian_mood_prior=0.4, implicit_intensity=0.5,
        prosody_estimate=None, anomaly_detected=False,
    )
    assert prior == pytest.approx(0.47)
    assert conf == pytest.approx(2 / 3)


def test_composite_prior_includes_prosody_when_confident():
    estimate = ProsodyEmotionEstimate(valence=-0.6, confidence=0.85)
    prior, conf = asm.compute_composite_prior(
        circadian_mood_prior=0.4, implicit_intensity=0.5,
        prosody_estimate=estimate, anomaly_detected=False,
    )
    assert prior == pytest.approx(0.535)
    assert conf == pytest.approx(1.0)


def test_composite_prior_ignores_low_confidence_prosody():
    estimate = ProsodyEmotionEstimate(valence=-0.6, confidence=0.3)  # below 0.4 threshold
    prior, conf = asm.compute_composite_prior(
        circadian_mood_prior=0.4, implicit_intensity=0.5,
        prosody_estimate=estimate, anomaly_detected=False,
    )
    assert prior == pytest.approx(0.47)
    assert conf == pytest.approx(2 / 3)


def test_composite_prior_anomaly_bonus():
    prior, _ = asm.compute_composite_prior(
        circadian_mood_prior=0.4, implicit_intensity=0.5,
        prosody_estimate=None, anomaly_detected=True,
    )
    assert prior == pytest.approx(0.55)


def test_composite_prior_clamped_to_one():
    prior, _ = asm.compute_composite_prior(
        circadian_mood_prior=1.0, implicit_intensity=1.0,
        prosody_estimate=ProsodyEmotionEstimate(valence=-1.0, confidence=0.9),
        anomaly_detected=True,
    )
    assert prior == 1.0


# ── Conflict rule 1: low-vulnerability band vs high implicit intensity (§7.2) ─
def test_effective_circadian_raised_by_high_implicit_in_low_vuln_band():
    # morning prior 0.20, implicit 0.9 → max(0.20, 0.9*0.8=0.72) = 0.72
    assert asm.resolve_effective_circadian(0.20, 0.9) == pytest.approx(0.72)


def test_effective_circadian_unchanged_in_high_vuln_band():
    # late_night prior 0.75 is not a low-vulnerability band → no override
    assert asm.resolve_effective_circadian(0.75, 0.9) == 0.75


def test_effective_circadian_unchanged_when_implicit_low():
    assert asm.resolve_effective_circadian(0.20, 0.3) == 0.20


# ── Conflict rule 2: prosody mismatch (§7.2) ─────────────────────────────────
def test_signal_mismatch_true_for_distressed_prosody():
    estimate = ProsodyEmotionEstimate(valence=-0.6,
                                      dominant_signal=ProsodyDominantSignal.DISTRESSED,
                                      confidence=0.8)
    assert asm.detect_signal_mismatch(estimate) is True


def test_signal_mismatch_false_for_positive_prosody():
    estimate = ProsodyEmotionEstimate(valence=0.5,
                                      dominant_signal=ProsodyDominantSignal.ANIMATED,
                                      confidence=0.8)
    assert asm.detect_signal_mismatch(estimate) is False


def test_signal_mismatch_false_without_prosody():
    assert asm.detect_signal_mismatch(None) is False


# ── Full assembly (§7.3) ─────────────────────────────────────────────────────
def _assemble(**overrides):
    base = dict(
        user_id=uuid4(),
        message_id=uuid4(),
        received_at=datetime(2026, 6, 26, 9, 0, 0),
        user_local_time=time(9, 0, 0),
        circadian_band="morning",
        circadian_mood_prior=0.20,
        day_of_week="Friday",
        is_weekend=False,
        session_gap_seconds=120,
        gap_category="same_session",
        human_readable_gap_label="just now",
        is_new_session=False,
        anomaly_detected=False,
        context_note=None,
        relationship_age_days=30,
        total_sessions_with_user=12,
        avg_session_frequency_days=2.5,
        gap_vs_baseline_ratio=0.5,
        due_threads=[],
        overdue_thread_count=0,
        fuzzy_label_for_timestamp=lambda ts: "earlier today",
        response_latency_ms=8000,
        latency_signal="quick",
        latency_deviation_from_baseline=None,
        deletion_occurred=False,
        deletion_count=0,
        final_length_vs_peak_ratio=None,
        message_length_chars=42,
        length_ratio_vs_baseline=1.0,
        initiation_type="continuation",
        is_message_burst=False,
        burst_count=1,
        implicit_emotional_intensity_score=0.0,
        modality_context=ModalityContext(primary_modality=PrimaryModality.TEXT,
                                          text_content="hi"),
        raw_text="hi",
        prosody_features=None,
        prosody_emotion_estimate=None,
    )
    base.update(overrides)
    return asm.assemble(**base)


def test_assemble_returns_complete_packet():
    packet = _assemble()
    assert isinstance(packet, InputPerceptionPacket)
    assert packet.primary_modality == "text"
    assert packet.fuzzy_label_for_timestamp(datetime(2026, 6, 26)) == "earlier today"
    # composite prior computed from circadian 0.20 + implicit 0.0
    assert packet.composite_emotional_prior == pytest.approx(0.06)
    assert packet.prior_confidence == pytest.approx(2 / 3)


def test_assemble_applies_conflict_rule_to_composite():
    # Low-vuln morning band with very high implicit intensity must raise the prior.
    packet = _assemble(circadian_mood_prior=0.20, implicit_emotional_intensity_score=0.9)
    # effective circadian = max(0.20, 0.72) = 0.72; composite = (0.72*0.15 + 0.9*0.35)/0.5
    assert packet.composite_emotional_prior == pytest.approx(0.846)


def test_assemble_sets_signal_mismatch_from_prosody():
    estimate = ProsodyEmotionEstimate(valence=-0.6,
                                      dominant_signal=ProsodyDominantSignal.DISTRESSED,
                                      confidence=0.8)
    packet = _assemble(prosody_emotion_estimate=estimate)
    assert packet.signal_mismatch is True
