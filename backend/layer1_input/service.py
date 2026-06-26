"""Layer 1 · Service entry point — ``process_input_event`` (architecture doc §12.2).

The single function the Conversation Orchestrator calls. It loads per-user state, runs the
five sub-components, and returns a fully-populated ``InputPerceptionPacket``.

Layer 1 is stateless in execution: it *reads* per-user state (temporal profile, narrative
threads, rolling baselines, voice calibration) but never writes it — the Layer 2 State Updater
persists everything after the turn completes (§8, §13). All store/​backend dependencies are
injected, so production SQLite/SQLCipher stores swap in without touching this module.

Hard rule (§11): a packet is ALWAYS emitted. Every backing-store read is guarded; on failure
the pipeline falls back to safe defaults rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Protocol
from uuid import UUID, uuid4

from . import assembler, implicit_signals, multimodal_normalizer, prosody_extractor
from . import temporal_resolver as tr
from . import thread_tracker
from .multimodal_normalizer import NormalizerBackends
from .prosody_extractor import ProsodyBackend
from .schemas import (
    AttachmentPayload,
    AttachmentType,
    ClientMetadata,
    InputPerceptionPacket,
    ModalityContext,
    PrimaryModality,
    UserBehaviorBaseline,
    UserTemporalProfile,
    VoiceCalibrationProfile,
)
from .thread_tracker import InMemoryThreadStore, ThreadStore


# ── Injectable per-user state stores ─────────────────────────────────────────
class ProfileStore(Protocol):
    def get(self, user_id: UUID) -> Optional[UserTemporalProfile]: ...


class InMemoryProfileStore:
    """Default in-process ProfileStore (tests / pre-DB). Missing user → cold start."""

    def __init__(self, profiles: Optional[dict[UUID, UserTemporalProfile]] = None) -> None:
        self._profiles = dict(profiles) if profiles else {}

    def get(self, user_id: UUID) -> Optional[UserTemporalProfile]:
        return self._profiles.get(user_id)


@dataclass
class Layer1Backends:
    """Heavy model backends for SC-3 / SC-4. All optional — absent → graceful degradation."""

    normalizer: NormalizerBackends = field(default_factory=NormalizerBackends)
    prosody: Optional[ProsodyBackend] = None


# ── Helpers ──────────────────────────────────────────────────────────────────
def _safe_get_profile(
    profile_store: ProfileStore, user_id: UUID
) -> tuple[UserTemporalProfile, bool]:
    """Return (profile, cold_start). Falls back to a fresh default if the read fails (§11)."""
    try:
        profile = profile_store.get(user_id)
    except Exception:  # noqa: BLE001 — store failure must never break the pipeline
        profile = None
    if profile is None:
        return UserTemporalProfile(user_id=user_id), True
    return profile, profile.total_sessions < tr.ANOMALY_MIN_SESSIONS


def _safe_due_threads(store: ThreadStore, now: datetime) -> tuple[list, int]:
    """Return (surfaced_threads, overdue_count); empty on failure (§11)."""
    try:
        candidates = thread_tracker.due_candidates(store, now)
    except Exception:  # noqa: BLE001
        return [], 0
    surfaced = candidates[: thread_tracker.MAX_SURFACED_THREADS]
    return surfaced, len(candidates) - len(surfaced)


def _first_voice_attachment(
    attachments: list[AttachmentPayload],
) -> Optional[AttachmentPayload]:
    for att in attachments:
        if att.attachment_type == AttachmentType.VOICE:
            return att
    return None


# ── Service entry point ──────────────────────────────────────────────────────
async def process_input_event(
    user_id: UUID,
    raw_message: Optional[str],
    received_at: datetime,
    attachments: list[AttachmentPayload],
    client_metadata: ClientMetadata,
    *,
    profile_store: Optional[ProfileStore] = None,
    thread_store: Optional[ThreadStore] = None,
    backends: Optional[Layer1Backends] = None,
    behavior_baseline: Optional[UserBehaviorBaseline] = None,
    voice_calibration: Optional[VoiceCalibrationProfile] = None,
    established_language: Optional[str] = None,
) -> InputPerceptionPacket:
    """Transform a raw incoming event into an ``InputPerceptionPacket`` (§2, §12.2)."""

    profile_store = profile_store or InMemoryProfileStore()
    thread_store = thread_store or InMemoryThreadStore()
    backends = backends or Layer1Backends()
    baseline = behavior_baseline or UserBehaviorBaseline()

    profile, cold_start = _safe_get_profile(profile_store, user_id)

    # ── SC-1: Temporal Resolver ─────────────────────────────────────────
    # Timezone: unknown for a cold-start profile → default UTC, low confidence (§11).
    timezone_confidence = "low" if cold_start else "high"
    local_dt = received_at + timedelta(hours=profile.timezone_offset_hours)
    band = tr.map_circadian_band(local_dt.hour)
    mood_prior = tr.circadian_mood_prior(band, profile)

    if profile.last_session_end is None:
        gap_seconds = 0
        is_new = True  # the user's very first turn is, by definition, a new session
    else:
        gap_seconds = max(0, int((received_at - profile.last_session_end).total_seconds()))
        is_new = tr.is_new_session(gap_seconds)
    gap_category = tr.classify_session_gap(gap_seconds)
    gap_label = tr.gap_label(gap_category)

    anomaly, context_note = tr.detect_temporal_anomaly(
        band, gap_seconds, profile, baseline.shortest_recent_gap_seconds
    )
    gap_ratio = tr.gap_vs_baseline_ratio(gap_seconds, profile)
    fuzzy_labeler = tr.make_fuzzy_labeler(received_at)
    due_threads, overdue_count = _safe_due_threads(thread_store, received_at)

    # ── SC-2: Implicit Signal Extractor ─────────────────────────────────
    latency_ms = implicit_signals.compute_latency(
        client_metadata.nova_last_delivered_at,
        client_metadata.user_typing_started_at,
        received_at,
    )
    latency_signal = implicit_signals.classify_latency(latency_ms)
    latency_dev = implicit_signals.latency_deviation(latency_ms, baseline.latency_median_ms)
    del_ratio = implicit_signals.deletion_ratio(
        client_metadata.peak_draft_length_chars, client_metadata.final_draft_length_chars
    )
    message_length = len(raw_message) if raw_message else 0
    len_ratio = implicit_signals.length_ratio(
        message_length, baseline.message_length_median_chars
    )
    initiation = implicit_signals.resolve_initiation_type(
        not is_new,  # ongoing session ⟺ not a new session (single SC-1 decision)
        client_metadata.is_reply_to_proactive,
        client_metadata.last_nova_message_was_proactive,
    )
    is_burst = implicit_signals.is_message_burst(
        client_metadata.is_burst, client_metadata.burst_count
    )
    intensity = implicit_signals.compute_implicit_emotional_intensity(
        latency_signal.value if latency_signal else None,
        client_metadata.deletion_occurred,
        client_metadata.deletion_count,
        len_ratio,
        initiation.value,
    )

    # ── SC-3: Multimodal Normalizer ─────────────────────────────────────
    modality_context = multimodal_normalizer.normalize(
        raw_message, attachments, backends.normalizer, established_language
    )

    # ── SC-4: Voice Prosody Extractor (only on a successfully transcribed voice note) ──
    prosody_features = None
    prosody_estimate = None
    voice_att = _first_voice_attachment(attachments)
    if voice_att is not None and modality_context.primary_modality == PrimaryModality.VOICE:
        prosody_features, prosody_estimate = prosody_extractor.extract_prosody(
            voice_att, backends.prosody, voice_calibration
        )

    # raw_text is the user's words however they arrived — typed, transcribed, or extracted.
    raw_text = raw_message if raw_message else modality_context.text_content

    # ── SC-5: Assembler ─────────────────────────────────────────────────
    return assembler.assemble(
        user_id=user_id,
        message_id=uuid4(),
        received_at=received_at,
        user_local_time=local_dt.time(),
        circadian_band=band.value,
        circadian_mood_prior=mood_prior,
        day_of_week=local_dt.strftime("%A"),
        is_weekend=local_dt.weekday() >= 5,
        session_gap_seconds=gap_seconds,
        gap_category=gap_category.value,
        human_readable_gap_label=gap_label,
        is_new_session=is_new,
        anomaly_detected=anomaly,
        context_note=context_note,
        relationship_age_days=profile.relationship_age_days,
        total_sessions_with_user=profile.total_sessions,
        avg_session_frequency_days=profile.average_session_frequency_days,
        gap_vs_baseline_ratio=gap_ratio,
        due_threads=due_threads,
        overdue_thread_count=overdue_count,
        fuzzy_label_for_timestamp=fuzzy_labeler,
        response_latency_ms=latency_ms,
        latency_signal=latency_signal.value if latency_signal else None,
        latency_deviation_from_baseline=latency_dev,
        deletion_occurred=client_metadata.deletion_occurred,
        deletion_count=client_metadata.deletion_count,
        final_length_vs_peak_ratio=del_ratio,
        message_length_chars=message_length,
        length_ratio_vs_baseline=len_ratio,
        initiation_type=initiation.value,
        is_message_burst=is_burst,
        burst_count=client_metadata.burst_count,
        implicit_emotional_intensity_score=intensity,
        modality_context=modality_context,
        raw_text=raw_text,
        prosody_features=prosody_features,
        prosody_emotion_estimate=prosody_estimate,
        cold_start_profile=cold_start,
        timezone_confidence=timezone_confidence,
    )
