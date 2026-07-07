"""HTTP request/response models for the Nova API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_mode: str
    cognitive_system: str
    crisis_active: bool
    crisis_tier: Optional[str] = None       # populated when crisis_active (frontend crisis UI)
    refined: bool
    tool_invoked: bool = False
    confabulation_guard: bool = False        # parity with the SSE `meta` frame
    session_id: str


# ── Voice (Layer 9 / Kokoro TTS) ──────────────────────────────────────────
class VoiceRequest(BaseModel):
    text: str
    conversation_mode: str = "casual"       # the mode /chat returned; mapped to Layer-9 prosody
    voice_id: str | None = None


# ── Tools (Layer 8) ──────────────────────────────────────────────────────
class ToolConfirmationOut(BaseModel):
    request_id: str
    tool_name: str
    action_type: str
    action_description: str
    tier: str
    reversible: bool = True


class ToolActionOut(BaseModel):
    action_id: str
    tool_name: str
    operation: str
    action_type: str
    outcome: str
    result_summary: str = ""
    undone: bool = False


class ToolResultOut(BaseModel):
    ok: bool
    tool_name: str = ""
    operation: str = ""
    outcome: str = ""
    result_summary: str = ""
    error_message: Optional[str] = None


# ── Goals ────────────────────────────────────────────────────────────────
class GoalCreate(BaseModel):
    title: str
    description: str = ""


class GoalOut(BaseModel):
    goal_id: str
    title: str
    status: str
    progress_score: float = 0.0
    description: str = ""


# ── Memory ───────────────────────────────────────────────────────────────
class MemoryOut(BaseModel):
    memory_id: str
    summary: str
    importance: float = 0.0
    created_at: Optional[str] = None
    topic_tags: list[str] = []


class SemanticOut(BaseModel):
    memory_id: str
    statement: str
    confidence: float = 0.0


class MemoryAuditOut(BaseModel):
    episodic: list[MemoryOut] = []
    semantic: list[SemanticOut] = []


# ── Safety ───────────────────────────────────────────────────────────────
class SafetyEventOut(BaseModel):
    tier: str
    confidence: float = 0.0
    detected_at: Optional[str] = None
    signal_types: list = []


# ── Onboarding ───────────────────────────────────────────────────────────
class OnboardingOut(BaseModel):
    cold_start_active: bool
    session_index: int = 0


# ── Sessions ─────────────────────────────────────────────────────────────
class SessionOut(BaseModel):
    session_key: str
    turn_count: int = 0


# ── Privacy (Layer 12) ───────────────────────────────────────────────────
class MemoryDeletionOut(BaseModel):
    deleted: int
    memory_id: str
    certificate: str
    cascade: str = ""


class IntegrityOut(BaseModel):
    status: str          # INTACT | TAMPER_DETECTED
    audit_chain_ok: bool
    privacy_chain_ok: bool


# ── Sync (Layer 12, zero-knowledge) ──────────────────────────────────────
class SyncDeltaIn(BaseModel):
    delta_id: str
    source_device: str
    seq: int = 0
    encrypted_payload: str        # opaque AES ciphertext — server never decrypts
    size_bytes: Optional[int] = None


class SyncPushOut(BaseModel):
    stored: bool
    delta_id: str


class SyncDeltaOut(BaseModel):
    cursor: int
    delta_id: str
    source_device: str
    seq: int
    encrypted_payload: str
    size_bytes: int = 0


class SyncPullOut(BaseModel):
    deltas: list[SyncDeltaOut] = []
    cursor: int = 0


class SyncStatusOut(BaseModel):
    total_deltas: int
    by_device: dict = {}
    latest_cursor: int = 0


# ── Proactivity (Layer 6) ────────────────────────────────────────────────
class ProactiveItemOut(BaseModel):
    item_id: str
    item_type: str
    status: str
    content_basis: str = ""
    current_priority: float = 0.0


# ── Longitudinal (Layer 10) ──────────────────────────────────────────────
class LongitudinalSummaryOut(BaseModel):
    summary_id: str
    week_start_date: Optional[str] = None
    week_end_date: Optional[str] = None
    session_count: int = 0
    dominant_theme: str = ""
    week_narrative: str = ""


# ── Relationship (Layer 4/5) ─────────────────────────────────────────────
class RelationshipOut(BaseModel):
    stage: str
    total_sessions: int = 0
    total_messages_exchanged: int = 0
    tie_strength: float = 0.0
    trust_score: float = 0.0
    # Learned communication-style calibration (Layer 4/5 persona learning).
    formality_preference: float = 0.5
    response_length_preference: float = 0.5
    question_tolerance: float = 0.5
    unsolicited_advice_tolerance: float = 0.5


# ── Admin (job trigger) ──────────────────────────────────────────────────
class JobRunOut(BaseModel):
    job: str
    result: dict = {}
