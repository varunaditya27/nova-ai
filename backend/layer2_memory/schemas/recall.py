"""SC-6 recall outputs + the MemoryPacket contract (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Union

from .episodic import EpisodicMemory
from .semantic import SemanticMemory
from .stm import ConversationTurn
from .uwm import CommunicationModel, LifeSituation, PersonNode, Stressor
from .audit_narrative import NarrativeChain

Memory = Union[EpisodicMemory, SemanticMemory]


@dataclass
class ScoredMemory:
    memory: Memory
    recall_score: float = 0.0
    effective_score: float = 0.0
    gate_value: float = 1.0
    components: dict = field(default_factory=dict)
    fuzzy_temporal_label: str = ""


@dataclass
class RecallResult:
    memories: list[ScoredMemory] = field(default_factory=list)   # max 3
    uwm_context: dict = field(default_factory=dict)
    total_candidates_evaluated: int = 0
    retrieval_mode: str = ""
    temperature_used: float = 0.0


@dataclass
class UWMContextSnapshot:
    user_profile_brief: str = ""
    relevant_people: list[PersonNode] = field(default_factory=list)
    active_stressors: list[Stressor] = field(default_factory=list)
    active_situations: list[LifeSituation] = field(default_factory=list)
    psychological_posture: dict = field(default_factory=dict)
    communication_preferences: Optional[CommunicationModel] = None


@dataclass
class MemoryPacket:
    stm_turns: list[ConversationTurn] = field(default_factory=list)
    recalled_memories: list[ScoredMemory] = field(default_factory=list)
    uwm_context: UWMContextSnapshot = field(default_factory=UWMContextSnapshot)
    active_narrative_chains: list[NarrativeChain] = field(default_factory=list)
    retrieval_metadata: RecallResult = field(default_factory=RecallResult)
    fuzzy_label_util: Optional[Callable[[datetime], str]] = None

    # Diagnostic flags (§15 fallback behaviors).
    recall_degraded: bool = False
    uwm_unavailable: bool = False
    cold_start: bool = False
    no_relevant_memories: bool = False
    confabulation_guard: bool = False
