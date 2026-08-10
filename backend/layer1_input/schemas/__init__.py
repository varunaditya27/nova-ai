"""Schemas for Layer 1 — Input Perception.

Every data structure produced or consumed by Layer 1 lives in this package, split by
sub-component (see ``docs/layer-1-architecture.md`` §7.3). This ``__init__`` re-exports
everything so ``from backend.layer1_input.schemas import X`` keeps working unchanged
regardless of which submodule ``X`` actually lives in.

Design principles (architecture doc §14):
  * Pure-Python / zero third-party dependencies — stdlib ``dataclasses`` + ``enum`` only.
  * Read-only contract objects. The pipeline builds an ``InputPerceptionPacket`` once and
    never mutates it afterwards.
  * Every field has an explicit default so a *partial* packet can always be emitted even
    when an optional sub-component (SC-3 / SC-4) did not fire (§7.3, §11 "always emit").

All enums subclass ``str`` so a packet field compares equal to its plain-string spelling
(``packet.circadian_band == "morning"``) while remaining type-checked.
"""

from __future__ import annotations

from .client import AttachmentPayload, ClientMetadata
from .enums import (
    AttachmentType,
    CircadianBand,
    DocumentType,
    GapCategory,
    ImportanceTier,
    InitiationType,
    LatencySignal,
    PrimaryModality,
    ProsodyDominantSignal,
    ThreadStatus,
    ThreadType,
)
from .modality import (
    DocumentSummary,
    ModalityContext,
    ProsodyEmotionEstimate,
    ProsodyFeatures,
    VoiceCalibrationProfile,
)
from .packet import InputPerceptionPacket
from .temporal import NarrativeThread, UserBehaviorBaseline, UserTemporalProfile

__all__ = [
    "AttachmentPayload",
    "AttachmentType",
    "CircadianBand",
    "ClientMetadata",
    "DocumentSummary",
    "DocumentType",
    "GapCategory",
    "ImportanceTier",
    "InitiationType",
    "InputPerceptionPacket",
    "LatencySignal",
    "ModalityContext",
    "NarrativeThread",
    "PrimaryModality",
    "ProsodyDominantSignal",
    "ProsodyEmotionEstimate",
    "ProsodyFeatures",
    "ThreadStatus",
    "ThreadType",
    "UserBehaviorBaseline",
    "UserTemporalProfile",
    "VoiceCalibrationProfile",
]
