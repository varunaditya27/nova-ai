"""Layer 4 — Persona, Personality & Response Generation.

Core question: *who is responding, and how?* Layer 4 converges every upstream signal
(temporal context, recalled memory, emotion/intent classification, empathy hypothesis,
conversation mode) into an actual response — language, tone, content, structure,
phrasing, and personality expression.

Three sequential sub-systems (architecture doc §1–2):

    Persona Engine (SC-1..SC-4)  →  PersonaPacket   (read-only governance object)
        SC-1  persona_resolver.resolve_persona_state
        SC-2  relationship_manager.compute_relationship_state
        SC-3  tone_calibrator.calibrate_voice
        SC-4  drift_detector.detect_drift
    Semantic Planner / Agent 4a (SC-5)  →  SemanticDraft       (semantic_planner)
    Emotion Refiner / Agent 4b  (SC-6)  →  FinalResponsePacket (emotion_refiner)

    packet_builder.build_final_response_packet orchestrates SC-1..SC-6.

Design invariants honored here:
- Persona is a structured governance layer, not a prompt prefix (§14.1).
- Content and tone are separated concerns — two stages, two models (§14.2).
- Relationship depth is a behavioral gate, not a preference (§14.3).
- Voice parameters translate numbers into language; no raw scores reach the LLM (§14.4).
- Identity under pressure uses hard rules, not soft preferences (§14.5, §11).
- Factual preservation is verified, not trusted (§14.6).
- Layer 4 always emits a non-empty FinalResponsePacket (§12).

Reconciliation: the May-28 scaffold modelled this layer as a learned ``PersonalityVector``
plus a post-session ``drift_controller`` (belief-update gate) and a ``prompt_builder``.
The implementation follows the authoritative architecture doc instead: the six SC
sub-components above. Per-session persona resolution lives in ``persona_resolver``; the
per-turn identity guard is ``drift_detector`` (a different concept from the scaffold's
post-session belief-update gate, which is a Layer 2 State-Updater concern); prompt
construction lives inside ``semantic_planner`` / ``emotion_refiner``. See architecture
doc §15 for the full as-built mapping. The two LLM calls (SC-5, SC-6) are injected as
callables so the layer runs and tests offline.
"""

from backend.layer4_persona.packet_builder import (
    assemble_persona_packet,
    build_final_response_packet,
)
from backend.layer4_persona.persona_resolver import (
    CORE_IDENTITY_ANCHORS,
    resolve_persona_state,
)
from backend.layer4_persona.relationship_manager import (
    compute_relationship_state,
    compute_session_delta,
    stage_for_sessions,
    update_tie_strength,
)
from backend.layer4_persona.tone_calibrator import calibrate_voice
from backend.layer4_persona.drift_detector import detect_drift
from backend.layer4_persona.semantic_planner import generate_semantic_draft
from backend.layer4_persona.emotion_refiner import (
    refine_emotion,
    should_skip_refinement,
)
from backend.layer4_persona.schemas import (
    DriftDetectionResult,
    FinalResponsePacket,
    PersonaPacket,
    PersonaState,
    RelationshipState,
    SemanticDraft,
    VoiceParameters,
)

__all__ = [
    "build_final_response_packet",
    "assemble_persona_packet",
    "resolve_persona_state",
    "CORE_IDENTITY_ANCHORS",
    "compute_relationship_state",
    "compute_session_delta",
    "stage_for_sessions",
    "update_tie_strength",
    "calibrate_voice",
    "detect_drift",
    "generate_semantic_draft",
    "refine_emotion",
    "should_skip_refinement",
    "DriftDetectionResult",
    "FinalResponsePacket",
    "PersonaPacket",
    "PersonaState",
    "RelationshipState",
    "SemanticDraft",
    "VoiceParameters",
]
