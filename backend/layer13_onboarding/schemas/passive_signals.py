"""SC-1 Passive signal bundle + its 8 component signals (architecture doc §4.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VocabularyRegister:
    avg_word_length: float = 0.0
    avg_sentence_length: float = 0.0
    uses_emoji: bool = False
    formality_delta: int = 0
    message_length: int = 0


@dataclass
class EmotionalExpressionStyle:
    style: str = "indirect"                         # direct|indirect
    confidence: float = 0.2


@dataclass
class TopicApproach:
    hedges_views: bool = False
    seeks_opinions: bool = False
    seeks_facts: bool = False
    context_builder: bool = False


@dataclass
class DisclosureComfort:
    density: float = 0.0
    level: str = "low"                              # low|medium|high


@dataclass
class NamedPersonSignal:
    name: str
    relationship_type: Optional[str] = None
    confidence: float = 0.0


@dataclass
class LifeContextSignals:
    life_phase_signal: Optional[str] = None         # student|working|None
    life_phase_confidence: float = 0.0


@dataclass
class UrgencySignal:
    level: str = "medium"                           # high|medium|low


@dataclass
class CommunicationStyleUpdate:
    avg_user_message_length: float = 0.0
    verbosity_preference: str = "medium"            # concise|medium|verbose
    sample_count: int = 0


@dataclass
class PassiveSignalBundle:
    vocabulary_register: VocabularyRegister = field(default_factory=VocabularyRegister)
    emotional_expression_style: EmotionalExpressionStyle = field(default_factory=EmotionalExpressionStyle)
    topic_approach: TopicApproach = field(default_factory=TopicApproach)
    self_disclosure_comfort: DisclosureComfort = field(default_factory=DisclosureComfort)
    temporal_pattern: Optional[str] = None
    named_entities: list = field(default_factory=list)
    life_context_signals: LifeContextSignals = field(default_factory=LifeContextSignals)
    urgency_signals: UrgencySignal = field(default_factory=UrgencySignal)
    communication_style: CommunicationStyleUpdate = field(default_factory=CommunicationStyleUpdate)
