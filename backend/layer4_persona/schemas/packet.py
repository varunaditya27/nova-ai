"""PersonaPacket (SC-1..SC-4 output), SC-5 SemanticDraft + validation, and the
Layer 4 output FinalResponsePacket (architecture doc §6.4, §7.5, §7.6, §8.6, §9).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from backend.layer2_memory.schemas import ConversationMode

from .drift import DriftDetectionResult
from .persona_state import PersonaState
from .relationship import RelationshipState
from .voice import VoiceParameters


@dataclass
class PersonaPacket:
    """Read-only constraint structure consumed by SC-5 and SC-6 (architecture doc §6.4)."""

    persona_state: PersonaState = field(default_factory=PersonaState)
    relationship_state: RelationshipState = field(default_factory=RelationshipState)
    voice_parameters: VoiceParameters = field(default_factory=VoiceParameters)
    drift_check_result: DriftDetectionResult = field(default_factory=DriftDetectionResult)

    # Computed summary fields for prompt injection (plain language)
    persona_instruction: str = ""
    tone_instruction: str = ""
    constraint_instruction: str = ""
    memory_reference_policy: str = ""
    question_policy: str = ""
    length_instruction: str = ""

    assembled_at: Optional[datetime] = None


@dataclass
class SemanticDraft:
    """Factual, task-complete draft — no emotional refinement (architecture doc §7.5)."""

    text: str = ""
    key_claims: list[str] = field(default_factory=list)
    memory_references_used: list[str] = field(default_factory=list)
    advice_included: bool = False
    thread_addressed: Optional[str] = None
    word_count: int = 0
    complexity_score: float = 0.0
    reasoning_trace: Optional[str] = None


@dataclass
class AdviceGateValidationResult:
    """Deterministic advice-gate compliance check (architecture doc §7.6)."""

    passed: bool = True
    violation: Optional[str] = None
    action: Optional[str] = None      # e.g. "strip_advice"


@dataclass
class FactualValidationResult:
    """Post-refinement factual-preservation check (architecture doc §8.6)."""

    passed: bool = True
    missing_claims: list[str] = field(default_factory=list)
    action: Optional[str] = None      # e.g. "reinsert"


@dataclass
class FinalResponsePacket:
    """Complete Layer 4 output, passed to all consuming layers (architecture doc §9)."""

    # Response content
    final_text: str = ""

    # Provenance
    semantic_draft: SemanticDraft = field(default_factory=SemanticDraft)
    refinement_applied: bool = False
    refinement_skipped_reason: Optional[str] = None

    # Validation results
    advice_gate_passed: bool = True
    factual_validation_passed: bool = True
    factual_claims_reinserted: list[str] = field(default_factory=list)

    # Drift check
    drift_check_result: DriftDetectionResult = field(default_factory=DriftDetectionResult)

    # Metadata for Layer 9 (Interaction Orchestrator)
    complexity_score: float = 0.0
    emotional_intensity: float = 0.0
    conversation_mode: str = ConversationMode.CASUAL.value
    suggested_thinking_pause_ms: int = 0

    # Metadata for Layer 2 (State Updater)
    memory_references_used: list[str] = field(default_factory=list)
    thread_addressed: Optional[str] = None
    new_thread_created: Optional[str] = None

    # Metadata for Layer 5 (Social Coaching)
    topic_domain: str = "other"
    intent_served: str = "casual_chat"

    # Set by Layer 5 SC-5 when a social-coaching observation is injected (§7.3).
    social_coaching_injected: bool = False
    coaching_type_injected: Optional[str] = None
    coaching_person_id: Optional[str] = None

    # Audit
    response_generated_at: Optional[datetime] = None
    total_generation_latency_ms: int = 0
    semantic_planner_latency_ms: int = 0
    emotion_refiner_latency_ms: int = 0
