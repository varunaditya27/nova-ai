"""Layer 8 — Tool Use & Actions.

When the user asks Nova to *do* something (not just think or respond), this layer orchestrates
the action: intent detection → parameter resolution → confirmation gate → execution → audit
recording. It is an action layer, not a safety layer — crisis detection and safeguarding live
in Layer 11 (see the reconciliation note below).

Sub-components:

    SC-1  tool_manager.py        — Tool Manager: orchestrates the full workflow, routes to plugins
    SC-2  confirmation_gate.py   — Confirmation Gate: risk profile → AUTO / SOFT / HARD tier
    SC-3  parameter_resolver.py  — Parameter Resolver: detect gaps, one clarifying question/turn
    SC-4  action_recorder.py     — Action Recorder: append-only, auditable execution log
    plugins/                     — ToolPlugin implementations on a uniform, swappable interface
                                   (calendar, email, notes, reminders, web_search)

Design commitments:
- High-risk actions require explicit confirmation; the gate only ever ratchets a tier up.
- Every action is recorded and user-inspectable (via Layer 12); the audit trail is append-only
  — undo is recorded, never erased. Deletes are archived (logical), so they can be undone.
- A sent email is the one genuinely irreversible action; its undo returns False by design.
- Plugins run offline: external backends (search API, calendar/email providers) and the
  intent/synthesis LLMs are injected as callables, defaulting to safe in-memory behavior.

Reconciliation (as-built): the repository's older `docs/layer-8-architecture.md` described a
"Crisis Detection & Safety Engine" at Layer 8. That was a numbering mismatch — crisis/safety is
fully specified and owned by Layer 11 (`docs/layer-11-architecture.md`: Ethical Guardrails,
Crisis Detection Engine, Escalation Protocol, Dependency Monitor). Layer 8 is Tool Use &
Actions, consistent with this scaffold, `infra/db/models/tools.py`, and `config/layer8.yaml`.
The architecture doc has been rewritten to match; the prior crisis text remains in git history.
"""

from backend.layer8_tools import (
    action_recorder,
    confirmation_gate,
    parameter_resolver,
    schemas,
    tool_manager,
)
from backend.layer8_tools.action_recorder import ActionRecorder
from backend.layer8_tools.confirmation_gate import (
    ACTION_TIER_BASE,
    compute_confirmation_tier,
    get_confirmation_request,
    requires_user_confirmation,
)
from backend.layer8_tools.parameter_resolver import (
    detect_parameter_gaps,
    generate_clarification_question,
    next_clarification,
    resolve_from_context,
    resolve_parameter,
)
from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.plugins.calendar_plugin import CalendarPlugin
from backend.layer8_tools.plugins.email_plugin import EmailPlugin
from backend.layer8_tools.plugins.notes_plugin import NotesPlugin
from backend.layer8_tools.plugins.reminders_plugin import RemindersPlugin
from backend.layer8_tools.plugins.web_search_plugin import WebSearchPlugin
from backend.layer8_tools.schemas import (
    ActionRecord,
    ActionType,
    Capability,
    ConfirmationRequest,
    ConfirmationTier,
    ParameterGap,
    RiskLevel,
    ToolIntent,
    ToolOutcome,
    ToolResult,
    ToolUseOutput,
    ValidationResult,
)
from backend.layer8_tools.tool_manager import ToolManager

__all__ = [
    # modules
    "action_recorder", "confirmation_gate", "parameter_resolver", "schemas", "tool_manager",
    # orchestrator + recorder
    "ToolManager", "ActionRecorder",
    # plugins
    "ToolPlugin", "CalendarPlugin", "EmailPlugin", "NotesPlugin", "RemindersPlugin",
    "WebSearchPlugin",
    # gate
    "ACTION_TIER_BASE", "compute_confirmation_tier", "get_confirmation_request",
    "requires_user_confirmation",
    # resolver
    "detect_parameter_gaps", "generate_clarification_question", "next_clarification",
    "resolve_from_context", "resolve_parameter",
    # schemas
    "ActionRecord", "ActionType", "Capability", "ConfirmationRequest", "ConfirmationTier",
    "ParameterGap", "RiskLevel", "ToolIntent", "ToolOutcome", "ToolResult", "ToolUseOutput",
    "ValidationResult",
]
