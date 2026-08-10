"""Layer 1 injectable per-user state stores + safe-read helpers (architecture doc §8, §11).

Split out of ``service.py`` — store plumbing, not turn orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from . import thread_tracker
from .config import Layer1Config
from .multimodal_normalizer import NormalizerBackends
from .prosody_extractor import ProsodyBackend
from .schemas import AttachmentPayload, AttachmentType, UserTemporalProfile
from .thread_tracker import ThreadStore


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


def _safe_get_profile(
    profile_store: ProfileStore, user_id: UUID, cfg: Optional[Layer1Config] = None
) -> tuple[UserTemporalProfile, bool]:
    """Return (profile, cold_start). Falls back to a fresh default if the read fails (§11)."""
    try:
        profile = profile_store.get(user_id)
    except Exception:  # noqa: BLE001 — store failure must never break the pipeline
        profile = None
    if profile is None:
        return UserTemporalProfile(user_id=user_id), True
    return profile, profile.total_sessions < (cfg or Layer1Config()).anomaly_min_sessions


def _safe_due_threads(
    store: ThreadStore, now: datetime, cfg: Optional[Layer1Config] = None
) -> tuple[list, int]:
    """Return (surfaced_threads, overdue_count); empty on failure (§11)."""
    try:
        candidates = thread_tracker.due_candidates(store, now, cfg)
        surfaced = thread_tracker.get_due_threads(store, now, cfg=cfg)
    except Exception:  # noqa: BLE001
        return [], 0
    return surfaced, len(candidates) - len(surfaced)


def _first_voice_attachment(
    attachments: list[AttachmentPayload],
) -> Optional[AttachmentPayload]:
    for att in attachments:
        if att.attachment_type == AttachmentType.VOICE:
            return att
    return None
