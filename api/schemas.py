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
    refined: bool
    tool_invoked: bool = False
    session_id: str


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
