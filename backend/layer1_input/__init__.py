"""Layer 1 — Input Perception & Temporal Awareness.

Transforms every raw incoming event into a rich, read-only ``InputPerceptionPacket`` before
any reasoning, memory retrieval, or response generation. Five sub-components run in sequence
(architecture doc §2):

  * SC-1 Temporal Resolver         — ``temporal_resolver``
  * SC-2 Implicit Signal Extractor — ``implicit_signals``
  * SC-3 Multimodal Normalizer     — ``multimodal_normalizer``
  * SC-4 Voice Prosody Extractor   — ``prosody_extractor``
  * SC-5 Input Perception Assembler — ``assembler``

The Conversation Orchestrator calls the single entry point ``process_input_event`` (in
``service``); pending-thread surfacing lives in ``thread_tracker``. The full contract is in
``schemas`` and ``docs/layer-1-architecture.md``.
"""

from .schemas import (
    AttachmentPayload,
    AttachmentType,
    CircadianBand,
    ClientMetadata,
    DocumentSummary,
    GapCategory,
    InitiationType,
    InputPerceptionPacket,
    LatencySignal,
    ModalityContext,
    NarrativeThread,
    PrimaryModality,
    ProsodyEmotionEstimate,
    ProsodyFeatures,
    UserBehaviorBaseline,
    UserTemporalProfile,
    VoiceCalibrationProfile,
)
from .service import (
    InMemoryProfileStore,
    Layer1Backends,
    ProfileStore,
    process_input_event,
)
from .thread_tracker import InMemoryThreadStore, ThreadStore

__all__ = [
    "process_input_event",
    "InputPerceptionPacket",
    "ClientMetadata",
    "AttachmentPayload",
    "AttachmentType",
    "ModalityContext",
    "NarrativeThread",
    "UserTemporalProfile",
    "UserBehaviorBaseline",
    "VoiceCalibrationProfile",
    "DocumentSummary",
    "ProsodyFeatures",
    "ProsodyEmotionEstimate",
    "CircadianBand",
    "GapCategory",
    "LatencySignal",
    "InitiationType",
    "PrimaryModality",
    "Layer1Backends",
    "ProfileStore",
    "InMemoryProfileStore",
    "ThreadStore",
    "InMemoryThreadStore",
]
