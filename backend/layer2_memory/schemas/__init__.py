"""Schemas for Layer 2 — Cognition & Memory.

The complete data contract for the Memory Arbiter and every sub-component, per
``docs/layer-2-architecture.md``. Pure-stdlib (`dataclasses` + `enum`); no ORM/pydantic.

Five memory types (storage group): Short-Term buffer, Episodic, Semantic, Identity, and the
User World Model. Processing/state types: recall scoring, audit trail, narrative chains, and
the ``MemoryPacket`` contract handed to downstream layers.

Split by sub-component into submodules; this ``__init__`` re-exports everything so
``from backend.layer2_memory.schemas import X`` keeps working unchanged regardless of which
submodule ``X`` actually lives in.
"""

from __future__ import annotations

from .audit_narrative import AuditEvent, ChainedEpisode, NarrativeChain
from .emotion import EmotionVector
from .enums import (
    AuditEventType,
    BASE_IMPORTANCE,
    ChainStatus,
    ConversationMode,
    IdentityCategory,
    ImportanceCategory,
    NarrativeLinkType,
    SemanticMemoryType,
)
from .episodic import EpisodicMemory, RecallEvent
from .fce import EpisodicCluster, FCERunReport
from .identity import BeliefUpdateEvent, IdentityContradiction, IdentityEvidence, IdentityMemory
from .recall import Memory, MemoryPacket, RecallResult, ScoredMemory, UWMContextSnapshot
from .semantic import SemanticMemory
from .stm import ConversationTurn, ShortTermMemoryBuffer
from .uwm import (
    CommunicationModel,
    LifeContext,
    LifeSituation,
    PersonNode,
    PsychologicalModel,
    RelationshipGraph,
    Stressor,
    TriggerPattern,
    UserProfile,
    UserWorldModel,
    UWMLifeEvent,
)

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "BASE_IMPORTANCE",
    "BeliefUpdateEvent",
    "ChainStatus",
    "ChainedEpisode",
    "CommunicationModel",
    "ConversationMode",
    "ConversationTurn",
    "EmotionVector",
    "EpisodicCluster",
    "EpisodicMemory",
    "FCERunReport",
    "IdentityCategory",
    "IdentityContradiction",
    "IdentityEvidence",
    "IdentityMemory",
    "ImportanceCategory",
    "LifeContext",
    "LifeSituation",
    "Memory",
    "MemoryPacket",
    "NarrativeChain",
    "NarrativeLinkType",
    "PersonNode",
    "PsychologicalModel",
    "RecallEvent",
    "RecallResult",
    "RelationshipGraph",
    "ScoredMemory",
    "SemanticMemory",
    "SemanticMemoryType",
    "ShortTermMemoryBuffer",
    "Stressor",
    "TriggerPattern",
    "UWMContextSnapshot",
    "UWMLifeEvent",
    "UserProfile",
    "UserWorldModel",
]
