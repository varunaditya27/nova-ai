"""Schemas for Layer 4 — Persona, Personality & Response Generation.

Layer 4 answers *who is responding and how*. It converges every upstream signal
(temporal context, recalled memory, emotion/intent classification, empathy
hypothesis, conversation mode) into an actual response: language, tone, content,
structure, phrasing, and personality expression.

The layer is three sequential sub-systems (architecture doc §1–2):

    Persona Engine (SC-1..SC-4)  →  PersonaPacket
        SC-1 Persona State Resolver      (persona_resolver.py)
        SC-2 Relationship State Manager  (relationship_manager.py)
        SC-3 Tone & Style Calibrator     (tone_calibrator.py)
        SC-4 Persona Drift Detector      (drift_detector.py)
    Semantic Planner / Agent 4a (SC-5)   →  SemanticDraft   (semantic_planner.py)
    Emotion Refiner / Agent 4b  (SC-6)   →  FinalResponsePacket (emotion_refiner.py)

The orchestrator (packet_builder.py) runs SC-1..SC-6 and emits the
``FinalResponsePacket`` consumed by Layers 2, 5, 6, 7, 9, 12.

Type reuse (single source of truth): this module imports the upstream packets and
the shared enums rather than redefining them. ``ConversationMode`` lives in
Layer 2; the emotion/intent classification types live in Layer 3.

Reconciliation note (architecture doc §3.4, §5.3): the doc references
``PsychologicalModel`` fields that do not exist in the implemented Layer 2 schema
(``humor_receptivity``, ``preferred_interaction_style``, ``known_sensitivities``).
The implemented resolver derives those signals from the fields that *do* exist —
``CommunicationModel.uses_humor`` / ``humor_style`` / ``prefers_direct_answers`` /
``vocabulary_complexity`` and ``PsychologicalModel.preferred_support_style`` /
``known_triggers`` — keeping the layer runnable against the real UWM. See §15
in the architecture doc for the full as-built mapping.

Pure stdlib (dataclasses + str-Enum) so the entire layer runs and tests offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

# ── Upstream types (single source of truth) ──────────────────────────────────
from backend.layer2_memory.schemas import (  # noqa: F401  (re-exported)
    ConversationMode,
    ConversationTurn,
    ScoredMemory,
    UWMContextSnapshot,
)
from backend.layer3_reasoning.schemas import (  # noqa: F401  (re-exported)
    AdviceGate,
    BackgroundEmotionalState,
    EmotionIntentPacket,
)


# ════════════════════════════════════════════════════════════════════════════
# SC-2 Relationship enums
# ════════════════════════════════════════════════════════════════════════════
class RelationshipStage(str, Enum):
    """Qualitative relationship phase (architecture doc §4.2)."""

    NEW = "new"                      # 0–3 sessions; first contact
    ACQUAINTANCE = "acquaintance"    # 4–15 sessions; getting to know
    DEVELOPING = "developing"        # 16–40 sessions; real depth forming
    ESTABLISHED = "established"      # 41–100 sessions; trusted, consistent
    CLOSE = "close"                  # 100+ sessions; genuinely close


class MemoryReferencePolicy(str, Enum):
    """How explicitly Nova may bring up past memories (architecture doc §4.4)."""

    NONE = "none"
    SOFT = "soft"        # vague: "I remember you mentioned something like this"
    EPISODIC = "episodic"  # can reference specific episodes
    FULL = "full"        # full episodic + semantic pattern references


# ════════════════════════════════════════════════════════════════════════════
# SC-3 Voice / tone enums
# ════════════════════════════════════════════════════════════════════════════
class Register(str, Enum):
    FORMAL = "formal"
    PROFESSIONAL = "professional"
    NATURAL = "natural"
    CASUAL = "casual"
    INTIMATE = "intimate"


class SentenceLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    MIXED = "mixed"


class ParagraphDensity(str, Enum):
    SPARSE = "sparse"
    NORMAL = "normal"
    DENSE = "dense"


class VocabularyTier(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    ELEVATED = "elevated"
    TECHNICAL = "technical"


class ContractionPolicy(str, Enum):
    ALWAYS = "always"
    PREFERRED = "preferred"
    AVOID = "avoid"
    NEVER = "never"


class HumorMode(str, Enum):
    NONE = "none"
    SUBTLE = "subtle"
    MODERATE = "moderate"
    PLAYFUL = "playful"


class HumorType(str, Enum):
    DRY = "dry"
    WORDPLAY = "wordplay"
    ABSURDIST = "absurdist"
    WARM = "warm"


class TargetResponseLength(str, Enum):
    VERY_SHORT = "very_short"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    ADAPTIVE = "adaptive"


class QuestionType(str, Enum):
    OPEN = "open"
    SPECIFIC = "specific"
    CHECKING_IN = "checking_in"
    NONE = "none"


class SelfDisclosureDepth(str, Enum):
    NONE = "none"
    SURFACE = "surface"
    MODERATE = "moderate"


# ════════════════════════════════════════════════════════════════════════════
# SC-4 Drift enums
# ════════════════════════════════════════════════════════════════════════════
class DriftType(str, Enum):
    SYCOPHANTIC_CAPITULATION = "sycophantic_capitulation"
    IDENTITY_CONTRADICTION = "identity_contradiction"
    FABRICATED_EMOTION = "fabricated_emotion"
    HARMFUL_VALIDATION = "harmful_validation"
    ROLE_ABANDONMENT = "role_abandonment"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedAction(str, Enum):
    PROCEED = "proceed"
    ADD_CAVEAT = "add_caveat"
    REDIRECT = "redirect"
    HOLD_POSITION = "hold_position"
    REFUSE_GRACEFULLY = "refuse_gracefully"


# ════════════════════════════════════════════════════════════════════════════
# SC-1 PersonaState
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class DynamicPersonaProperty:
    """A lower-centrality identity property that evolves over interactions (§3.3)."""

    key: str
    value: str = ""
    centrality: float = 0.0          # 0.0–0.84 (below the core threshold)
    confidence: float = 0.0
    last_updated: Optional[datetime] = None
    evidence_count: int = 0
    is_user_specific: bool = True


@dataclass
class PersonaState:
    """The current, authoritative in-session persona (architecture doc §3.4)."""

    # Core identity (always present)
    name: str = "Nova"
    character_description: str = ""
    primary_orientation: str = ""
    honesty_commitment: str = ""

    # Expression parameters (assembled from dynamic properties)
    warmth_level: float = 0.7
    humor_allowed: bool = False
    humor_frequency: float = 0.25
    directness_level: float = 0.6
    technical_depth_allowed: bool = False
    intellectual_engagement_level: float = 0.5

    # Boundary policies (hard constraints — always True)
    will_not_fabricate_emotions: bool = True
    will_not_be_sycophantic: bool = True
    will_disagree_when_warranted: bool = True
    will_not_catastrophize: bool = True

    # Session-specific overrides
    session_tone_override: Optional[str] = None
    user_nickname_for_nova: Optional[str] = None
    known_sensitivities: list[str] = field(default_factory=list)

    # Provenance
    core_anchors_loaded: int = 0
    dynamic_properties_loaded: int = 0
    last_identity_update: Optional[datetime] = None


# ════════════════════════════════════════════════════════════════════════════
# SC-2 RelationshipState
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class SessionSummary:
    """Per-session signals consumed by the tie-strength delta (architecture doc §4.3)."""

    had_vulnerability_moment: bool = False
    explicit_trust_signals_count: int = 0
    total_messages: int = 0
    max_emotional_intensity: float = 0.0
    repair_occurred: bool = False


@dataclass
class RelationshipState:
    """Multi-dimensional relationship model (architecture doc §4.2)."""

    # Tie strength
    tie_strength: float = 0.0
    relationship_age_days: int = 0
    total_sessions: int = 0
    total_messages_exchanged: int = 0

    # Stage
    stage: str = RelationshipStage.NEW.value

    # Intimacy model
    emotional_disclosure_depth: float = 0.0
    personal_topic_exposure: float = 0.0
    vulnerability_moments: int = 0
    reciprocity_score: float = 0.0

    # Trust
    trust_score: float = 0.0
    repair_events: int = 0
    explicit_trust_signals: int = 0

    # Communication-style calibration
    formality_preference: float = 0.5
    response_length_preference: float = 0.5
    question_tolerance: float = 0.5
    unsolicited_advice_tolerance: float = 0.5

    # Behavioral gates derived from stage (§4.4)
    self_disclosure_ceiling: str = SelfDisclosureDepth.SURFACE.value
    memory_reference_policy: str = MemoryReferencePolicy.NONE.value
    follow_up_question_ceiling: int = 1
    direct_noticing_allowed: bool = False


# ════════════════════════════════════════════════════════════════════════════
# SC-3 VoiceParameters
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class VoiceParameters:
    """Precise, deterministic style directives for the two planners (§5.2)."""

    # Register
    register: str = Register.NATURAL.value
    register_note: str = ""

    # Sentence structure
    sentence_length: str = SentenceLength.MEDIUM.value
    paragraph_density: str = ParagraphDensity.NORMAL.value
    use_lists: bool = False
    use_markdown: bool = False

    # Lexical
    vocabulary_tier: str = VocabularyTier.STANDARD.value
    contraction_policy: str = ContractionPolicy.PREFERRED.value
    filler_expression_allowed: bool = False

    # Emotional expression
    warmth_expression: float = 0.6
    empathy_explicitness: float = 0.3
    validation_first: bool = False
    celebration_energy: float = 0.0

    # Humor
    humor_mode: str = HumorMode.NONE.value
    humor_type: str = HumorType.DRY.value

    # Length
    target_response_length: str = TargetResponseLength.SHORT.value
    max_response_length_chars: int = 500

    # Epistemic stance
    hedging_level: float = 0.1
    certainty_phrase_allowed: bool = True
    opinion_expression_allowed: bool = True

    # Follow-up question policy
    follow_up_question_allowed: bool = True
    follow_up_question_max: int = 1
    question_type: str = QuestionType.OPEN.value

    # Self-disclosure
    self_disclosure_allowed: bool = False
    self_disclosure_depth: str = SelfDisclosureDepth.NONE.value


# ════════════════════════════════════════════════════════════════════════════
# SC-4 DriftDetectionResult
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class DriftDetectionResult:
    """Per-turn identity-consistency guard result (architecture doc §6.2)."""

    drift_detected: bool = False
    drift_type: Optional[str] = None
    affected_anchor: Optional[str] = None
    risk_level: str = RiskLevel.LOW.value
    recommended_action: str = RecommendedAction.PROCEED.value
    drift_note: Optional[str] = None
    # Plain-language directive injected into the Semantic Planner when drift fires.
    planner_directive: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# PersonaPacket — output of SC-1 through SC-4
# ════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════
# SC-5 SemanticDraft + validation
# ════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════
# FinalResponsePacket — Layer 4 output
# ════════════════════════════════════════════════════════════════════════════
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
