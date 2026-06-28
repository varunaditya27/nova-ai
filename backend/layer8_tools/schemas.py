"""Schemas for Layer 8 — Tool Use & Actions (architecture doc §3).

Pure-stdlib dataclasses + str-enums (the test runtime has no pydantic). These are the data
contract shared by the Confirmation Gate, Parameter Resolver, Tool Manager, Action Recorder,
and every plugin. Plugins describe themselves with ``Capability`` objects, so the gate and
resolver read risk/reversibility/required-params off the capability rather than hard-coding
per-tool rules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


# ── Enums ────────────────────────────────────────────────────────────────────
class ConfirmationTier(str, Enum):
    """How much user assent an action needs before it executes (§4)."""
    AUTO = "auto"   # low risk, reversible — execute immediately
    SOFT = "soft"   # ask, but a non-objection / timeout proceeds
    HARD = "hard"   # require explicit confirmation before executing


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """The CRUD-ish verb an operation maps to; drives the base confirmation tier."""
    READ = "read"
    SEARCH = "search"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEND = "send"


class ToolOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"      # awaiting confirmation
    CANCELLED = "cancelled"  # user declined at the gate


# ── Plugin self-description ───────────────────────────────────────────────────
@dataclass
class Capability:
    """One operation a plugin exposes, with the metadata the gate/resolver need."""
    operation: str                       # e.g. "create_event", "send"
    action_type: str = ActionType.READ.value
    description: str = ""
    default_tier: Optional[str] = None   # plugin override; None → derive from action_type
    reversible: bool = True
    external_impact: bool = False        # touches systems outside Nova (email/calendar)
    risk_level: str = RiskLevel.LOW.value
    required_params: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)


# ── Intent + parameter resolution ─────────────────────────────────────────────
@dataclass
class ToolIntent:
    """A parsed intent to use a tool (§5)."""
    tool_name: str
    operation: str
    action_type: str = ActionType.READ.value
    parameters: dict = field(default_factory=dict)
    parameters_missing: list[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_text: str = ""


@dataclass
class ParameterGap:
    """A missing/unresolved parameter the resolver must fill (§6)."""
    parameter_name: str
    description: str = ""
    required: bool = True
    prompt_hint: str = ""


# ── Confirmation ──────────────────────────────────────────────────────────────
@dataclass
class ConfirmationRequest:
    tool_name: str
    action_type: str
    action_description: str
    tier: str = ConfirmationTier.SOFT.value
    risk_level: str = RiskLevel.LOW.value
    reversible: bool = True
    parameters: dict = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Execution results + audit ─────────────────────────────────────────────────
@dataclass
class ToolResult:
    tool_name: str
    operation: str
    outcome: str = ToolOutcome.SUCCESS.value
    result_summary: str = ""
    data: Any = None
    error_message: Optional[str] = None
    undo_token: Optional[str] = None     # opaque handle for ActionRecorder/undo


@dataclass
class ActionRecord:
    """Append-only audit record of a tool execution (§7)."""
    tool_name: str
    operation: str
    action_type: str = ActionType.READ.value
    parameters: dict = field(default_factory=dict)
    outcome: str = ToolOutcome.SUCCESS.value
    result_summary: str = ""
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    user_session_id: Optional[str] = None
    linked_episodic_memory_id: Optional[str] = None
    undoable: bool = False
    undo_token: Optional[str] = None
    undone: bool = False
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ── Top-level Layer 8 output (§8) ─────────────────────────────────────────────
@dataclass
class ToolUseOutput:
    """What Layer 8 hands back to the pipeline for one message."""
    tool_invoked: bool = False
    intent: Optional[ToolIntent] = None
    confirmation_request: Optional[ConfirmationRequest] = None  # set when assent is needed
    clarification_question: Optional[str] = None                # set when a param is missing
    result: Optional[ToolResult] = None
    action_record: Optional[ActionRecord] = None
