"""HTTP request/response models for the Nova API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class EchoOut(BaseModel):
    """A memory Nova recalled while writing this turn (rendered as a tiny, dismissible 'echo')."""
    summary: str
    when: Optional[str] = None               # human label, e.g. "a few weeks ago"
    created_at: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_mode: str
    cognitive_system: str
    crisis_active: bool
    crisis_tier: Optional[str] = None       # populated when crisis_active (frontend crisis UI)
    refined: bool
    tool_invoked: bool = False
    confabulation_guard: bool = False        # parity with the SSE `meta` frame
    echoes: list[EchoOut] = []               # what Nova recalled this turn (Principle 7)
    session_id: str


# ── Conversation log (the permanent thread) ──────────────────────────────
class MessageOut(BaseModel):
    message_id: str
    cursor: int = 0                          # monotonic row id; pass the last item's as `before=` to page back
    role: str                                # "user" | "nova"
    content: str
    created_at: Optional[str] = None
    session_key: str = ""
    conversation_mode: Optional[str] = None
    crisis_active: bool = False
    tool_invoked: bool = False
    echoes: list[EchoOut] = []
    bookmarked: bool = False
    bookmark_category: Optional[str] = None
    is_milestone: bool = False
    milestone_label: Optional[str] = None


class BookmarkIn(BaseModel):
    category: Optional[str] = None


class MilestoneIn(BaseModel):
    label: Optional[str] = None


# ── Continuity / Digital Desk ────────────────────────────────────────────
class HomeOut(BaseModel):
    greeting: str                            # "Good evening"
    current_chapter: Optional[str] = None    # latest longitudinal narrative/theme
    relationship_stage: str = "new"
    last_interaction_at: Optional[str] = None
    weather: str = "clear"                   # relationship "weather" from recency
    active_goals: int = 0
    top_proactive: Optional[str] = None      # the thought Nova is holding
    cold_start_active: bool = False
    message_count: int = 0


class CalendarOut(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    days: dict = {}                          # {"2026-07-07": 12, ...} message counts per day


class MuseumEntryOut(BaseModel):
    label: str                               # "First conversation", "First milestone", …
    content: str = ""
    when: Optional[str] = None


class MuseumOut(BaseModel):
    entries: list[MuseumEntryOut] = []


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


class GoalUpdate(BaseModel):
    status: str | None = None
    progress_score: float | None = None


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
    safety_chain_ok: bool


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
