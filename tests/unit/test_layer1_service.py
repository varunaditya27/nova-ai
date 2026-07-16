"""End-to-end tests for Layer 1 — process_input_event (architecture doc §12.2, §11).

Drives the whole SC-1…SC-5 pipeline through the single service entry point, covering the
text fast path, returning-user temporal context, multimodal/voice paths, thread surfacing,
and the §11 hard rule: a packet is ALWAYS emitted, even when a backing store fails.
"""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from backend.layer1_input import service as svc
from backend.layer1_input import thread_tracker as tt
from backend.layer1_input import multimodal_normalizer as mm
from backend.layer1_input.schemas import (
    AttachmentPayload,
    AttachmentType,
    ClientMetadata,
    ImportanceTier,
    InputPerceptionPacket,
    NarrativeThread,
    ProsodyDominantSignal,
    ProsodyEmotionEstimate,
    ProsodyFeatures,
    ThreadStatus,
    ThreadType,
    UserBehaviorBaseline,
    UserTemporalProfile,
)

NOW = datetime(2026, 6, 26, 20, 0, 0)  # 20:00 UTC


def _run(coro):
    return asyncio.run(coro)


def _client(**kw):
    base = dict(session_id=uuid4())
    base.update(kw)
    return ClientMetadata(**base)


# ── Fake backends ────────────────────────────────────────────────────────────
class FakeImageBackend:
    def describe(self, attachment):
        return mm.ImageResult(semantic_description="a sunset photo", image_type="ambient")


class FakeVoiceBackend:
    def transcribe(self, attachment):
        return mm.VoiceTranscript(transcript="I guess I'm okay", language_detected="en",
                                  confidence=0.9)


class FakeProsodyBackend:
    def extract(self, attachment, calibration):
        return (
            ProsodyFeatures(speech_rate_words_per_min=160.0, voice_tremor_detected=True),
            ProsodyEmotionEstimate(valence=-0.5, arousal=0.7, confidence=0.8,
                                   dominant_signal=ProsodyDominantSignal.DISTRESSED),
        )


# ── Text fast path / cold start ──────────────────────────────────────────────
def test_text_cold_start_returns_packet():
    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message="hey", received_at=NOW,
        attachments=[], client_metadata=_client(),
    ))
    assert isinstance(packet, InputPerceptionPacket)
    assert packet.primary_modality == "text"
    assert packet.raw_text == "hey"
    assert packet.cold_start_profile is True
    assert packet.timezone_confidence == "low"
    assert packet.initiation_type == "user_initiated_cold"
    assert packet.anomaly_detected is False  # no anomaly detection before 5 sessions
    assert packet.message_length_chars == 3


def test_returning_user_temporal_context():
    user_id = uuid4()
    profile = UserTemporalProfile(
        user_id=user_id,
        timezone_offset_hours=0.0,
        total_sessions=30,
        average_session_frequency_days=1.0,
        typical_bands={"evening": 0.5, "night": 0.5},
        last_session_end=NOW - timedelta(days=2),
    )
    store = svc.InMemoryProfileStore({user_id: profile})
    packet = _run(svc.process_input_event(
        user_id=user_id, raw_message="back again", received_at=NOW,
        attachments=[], client_metadata=_client(),
        profile_store=store,
    ))
    assert packet.gap_category == "few_days"
    assert packet.is_new_session is True
    assert packet.gap_vs_baseline_ratio == 2.0
    assert packet.circadian_band == "evening"
    assert packet.fuzzy_label_for_timestamp(NOW - timedelta(days=2)) == "a couple of days ago"


def test_latency_signal_computed_from_client_metadata():
    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message="ok", received_at=NOW,
        attachments=[],
        client_metadata=_client(
            nova_last_delivered_at=NOW - timedelta(seconds=5),
            user_typing_started_at=NOW - timedelta(seconds=1),
        ),
    ))
    # 4 s between Nova delivery and typing start → "quick"
    assert packet.response_latency_ms == 4000
    assert packet.latency_signal == "quick"


def test_self_censorship_and_long_message_raise_intensity():
    long_text = "x" * 400
    baseline = UserBehaviorBaseline(message_length_median_chars=50.0)
    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message=long_text, received_at=NOW,
        attachments=[],
        client_metadata=_client(deletion_occurred=True, deletion_count=4,
                                peak_draft_length_chars=900, final_draft_length_chars=400),
        behavior_baseline=baseline,
    ))
    assert packet.deletion_occurred is True
    assert packet.length_ratio_vs_baseline == 8.0
    assert packet.implicit_emotional_intensity_score > 0.3


# ── Multimodal paths ─────────────────────────────────────────────────────────
def test_image_path_with_backend():
    backends = svc.Layer1Backends(
        normalizer=mm.NormalizerBackends(image=FakeImageBackend()))
    att = AttachmentPayload(attachment_type=AttachmentType.IMAGE, mime_type="image/png",
                            data=b"\x89PNG")
    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message=None, received_at=NOW,
        attachments=[att], client_metadata=_client(), backends=backends,
    ))
    assert packet.primary_modality == "image"
    assert packet.modality_context.semantic_description == "a sunset photo"


def test_voice_path_runs_prosody_and_sets_mismatch():
    backends = svc.Layer1Backends(
        normalizer=mm.NormalizerBackends(voice=FakeVoiceBackend()),
        prosody=FakeProsodyBackend(),
    )
    att = AttachmentPayload(attachment_type=AttachmentType.VOICE, mime_type="audio/ogg",
                            data=b"OggS")
    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message=None, received_at=NOW,
        attachments=[att], client_metadata=_client(), backends=backends,
    ))
    assert packet.primary_modality == "voice"
    assert packet.raw_text == "I guess I'm okay"          # transcript flows into raw_text
    assert packet.prosody_emotion_estimate is not None
    assert packet.prosody_features.voice_tremor_detected is True
    assert packet.signal_mismatch is True                  # distressed prosody
    assert packet.modality_context.raw_voice_available is False  # raw audio discarded


def test_voice_untranscribed_skips_prosody():
    class LowConfVoice:
        def transcribe(self, attachment):
            return mm.VoiceTranscript(transcript="...", confidence=0.2)

    backends = svc.Layer1Backends(
        normalizer=mm.NormalizerBackends(voice=LowConfVoice()),
        prosody=FakeProsodyBackend(),
    )
    att = AttachmentPayload(attachment_type=AttachmentType.VOICE, data=b"OggS")
    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message=None, received_at=NOW,
        attachments=[att], client_metadata=_client(), backends=backends,
    ))
    assert packet.primary_modality == "voice_untranscribed"
    assert packet.prosody_emotion_estimate is None  # SC-4 skipped per §11


# ── Thread surfacing ─────────────────────────────────────────────────────────
def test_due_threads_surface_with_overdue_count():
    store = tt.InMemoryThreadStore()
    for w in (0.9, 0.8, 0.7):
        store.add(NarrativeThread(
            thread_id=uuid4(), summary="follow up", created_at=NOW - timedelta(days=5),
            follow_up_due_at=NOW - timedelta(hours=1), status=ThreadStatus.UNRESOLVED,
            emotional_weight=w, importance_tier=ImportanceTier.HIGH,
            thread_type=ThreadType.EMOTIONAL_SITUATION,
        ))
    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message="hi", received_at=NOW,
        attachments=[], client_metadata=_client(), thread_store=store,
    ))
    assert len(packet.due_threads) == 2
    assert packet.overdue_thread_count == 1


def test_safe_due_threads_delegates_slicing_to_get_due_threads(monkeypatch):
    """service.py should call thread_tracker.get_due_threads, not re-slice candidates inline."""
    calls = []
    real_get_due_threads = tt.get_due_threads

    def spy(store, now, max_threads=tt.MAX_SURFACED_THREADS):
        calls.append((store, now))
        return real_get_due_threads(store, now, max_threads)

    monkeypatch.setattr(svc.thread_tracker, "get_due_threads", spy)

    store = tt.InMemoryThreadStore()
    surfaced, overdue = svc._safe_due_threads(store, NOW)
    assert calls, "service._safe_due_threads should call thread_tracker.get_due_threads"
    assert surfaced == []
    assert overdue == 0


# ── §11 hard rule: always emit ───────────────────────────────────────────────
def test_packet_emitted_even_when_profile_store_fails():
    class ExplodingProfileStore:
        def get(self, user_id):
            raise RuntimeError("db unavailable")

    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message="still here", received_at=NOW,
        attachments=[], client_metadata=_client(),
        profile_store=ExplodingProfileStore(),
    ))
    assert isinstance(packet, InputPerceptionPacket)
    assert packet.cold_start_profile is True  # fell back to a default profile


def test_packet_emitted_even_when_thread_store_fails():
    class ExplodingThreadStore:
        def get_all(self, status=None):
            raise RuntimeError("threads.db unavailable")

    packet = _run(svc.process_input_event(
        user_id=uuid4(), raw_message="hi", received_at=NOW,
        attachments=[], client_metadata=_client(),
        thread_store=ExplodingThreadStore(),
    ))
    assert isinstance(packet, InputPerceptionPacket)
    assert packet.due_threads == []  # graceful empty per §11
