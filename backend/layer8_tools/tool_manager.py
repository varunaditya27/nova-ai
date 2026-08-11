"""SC: Tool Manager (architecture doc §5) — the Layer 8 orchestrator.

Sequences the full tool-use workflow for one message:

    detect intent → resolve missing params → confirmation gate → execute → record

The manager never performs actions itself; it routes to plugins through the uniform
``ToolPlugin`` interface, which makes them swappable. A missing required parameter
short-circuits with a single clarification question. Intent detection is an injected
``intent_fn`` (an LLM in production) with a keyword fallback so the layer works offline.

Security model (§5.1):

- **Confirmation is a bound, single-use capability token, not a boolean.** A SOFT/HARD action
  returns a ``ConfirmationRequest`` whose ``request_id`` is bound to a fingerprint of the exact
  action ``(tool, operation, parameters, user_id)``. Execution requires presenting that token
  back via ``confirm_action`` (or ``confirmation_id=`` on the direct path). This closes three
  vectors at once: replay (tokens are consumed on use), confused-deputy (a token for action A
  fails the fingerprint check for action B), and cross-user use (user_id is in the fingerprint).
- **The direct path is fail-closed.** ``execute_tool`` runs an AUTO operation freely, but a
  gated (SOFT/HARD) operation without a valid matching token is refused — there is no side door
  around the gate.
- **Undo enforces ownership.** ``undo_action`` refuses to reverse an action owned by another user.
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer8_tools import confirmation_gate, parameter_resolver
from backend.layer8_tools.action_recorder import ActionRecorder
from backend.layer8_tools.direct_execution import execute_tool_direct
from backend.layer8_tools.intent_routing import (
    coerce_intent,
    extract_search_query,
    keyword_intent,
    keyword_route,
)
from backend.layer8_tools.pending_confirmation import Pending as _Pending
from backend.layer8_tools.pending_confirmation import fingerprint as _fingerprint
from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.schemas import (
    ToolIntent,
    ToolOutcome,
    ToolResult,
    ToolUseOutput,
)

__all__ = ["ToolManager", "extract_search_query", "keyword_route"]


class ToolManager:
    def __init__(
        self,
        recorder: Optional[ActionRecorder] = None,
        intent_fn: Optional[Callable[[str], object]] = None,
    ) -> None:
        self.recorder = recorder or ActionRecorder()
        self._intent_fn = intent_fn
        self._plugins: dict[str, ToolPlugin] = {}
        self._pending: dict[str, _Pending] = {}   # request_id → bound confirmation

    # ── Registration / routing ────────────────────────────────────────────────
    def register_plugin(self, plugin: ToolPlugin) -> None:
        self._plugins[plugin.name] = plugin

    def get_plugin(self, tool_name: str) -> Optional[ToolPlugin]:
        return self._plugins.get(tool_name)

    # ── Intent detection ──────────────────────────────────────────────────────
    def detect_intent(self, message: str) -> Optional[ToolIntent]:
        if self._intent_fn is not None:
            return coerce_intent(self._intent_fn(message))
        return keyword_intent(message or "")

    # ── Full per-message orchestration ────────────────────────────────────────
    def process(
        self, message: str, user_id: Optional[str] = None,
        context: str = "", session_id: Optional[str] = None,
    ) -> ToolUseOutput:
        intent = self.detect_intent(message)
        if intent is None:
            return ToolUseOutput(tool_invoked=False)

        plugin = self.get_plugin(intent.tool_name)
        if plugin is None or not plugin.supports(intent.operation):
            return ToolUseOutput(tool_invoked=False, intent=intent)

        cap = plugin.capability_for(intent.operation)

        # 1) Missing required parameter → ask exactly one question.
        question = parameter_resolver.next_clarification(intent, cap)
        if question:
            return ToolUseOutput(tool_invoked=False, intent=intent, clarification_question=question)

        # 2) Confirmation gate → SOFT/HARD register a bound token and short-circuit.
        tier = self._tier_for(cap)
        if confirmation_gate.requires_user_confirmation(tier):
            req = confirmation_gate.get_confirmation_request(
                intent.tool_name, cap.action_type, self._describe(intent, cap), tier,
                cap.risk_level, cap.reversible, intent.parameters)
            self._pending[req.request_id] = _Pending(
                fingerprint=_fingerprint(intent.tool_name, intent.operation,
                                         intent.parameters, user_id),
                tool_name=intent.tool_name, operation=intent.operation,
                parameters=intent.parameters, action_type=cap.action_type,
                user_id=user_id, session_id=session_id,
                tier=tier, reversible=cap.reversible)
            return ToolUseOutput(tool_invoked=False, intent=intent, confirmation_request=req)

        # 3) AUTO → execute + record.
        result, record = self._execute_and_record(
            plugin, intent.operation, intent.parameters, cap.action_type, user_id, session_id)
        return ToolUseOutput(tool_invoked=True, intent=intent, result=result, action_record=record)

    def confirm_action(self, request_id: str, user_id: Optional[str] = None) -> ToolUseOutput:
        """Execute the action a confirmation token was issued for (§5.1).

        Single-use and ownership-checked: a wrong user is refused without consuming the token;
        a successful confirmation consumes it so it cannot be replayed.
        """
        pending = self._pending.get(request_id)
        if pending is None:
            return ToolUseOutput(tool_invoked=False)           # unknown / expired / already used
        if pending.user_id != user_id:
            return ToolUseOutput(tool_invoked=False)           # ownership mismatch — keep token
        del self._pending[request_id]                          # consume (anti-replay)

        plugin = self.get_plugin(pending.tool_name)
        if plugin is None or not plugin.supports(pending.operation):
            return ToolUseOutput(tool_invoked=False)
        result, record = self._execute_and_record(
            plugin, pending.operation, pending.parameters, pending.action_type,
            pending.user_id, pending.session_id)
        return ToolUseOutput(tool_invoked=True, result=result, action_record=record)

    @staticmethod
    def _tier_for(cap) -> str:
        return confirmation_gate.compute_confirmation_tier(
            cap.action_type, reversible=cap.reversible, external_impact=cap.external_impact,
            risk_level=cap.risk_level, base_tier=cap.default_tier)

    @staticmethod
    def _describe(intent: ToolIntent, cap) -> str:
        detail = ", ".join(f"{k}={v}" for k, v in (intent.parameters or {}).items())
        base = cap.description or f"{intent.tool_name} {intent.operation}"
        return f"{base} ({detail})" if detail else base

    # ── Direct execution (fail-closed on gated tiers) ─────────────────────────
    def execute_tool(
        self, tool_name: str, operation: str, parameters: dict,
        user_id: Optional[str] = None, session_id: Optional[str] = None,
        action_type: Optional[str] = None, confirmation_id: Optional[str] = None,
    ) -> ToolResult:
        return execute_tool_direct(
            self, tool_name, operation, parameters,
            user_id=user_id, session_id=session_id,
            action_type=action_type, confirmation_id=confirmation_id)

    def _execute_and_record(self, plugin, operation, parameters, action_type, user_id, session_id):
        try:
            result = plugin.execute(operation, parameters)
        except Exception as exc:  # degrade, never raise into the pipeline
            result = ToolResult(plugin.name, operation, ToolOutcome.FAILURE.value,
                                error_message=f"execution error: {exc}")
        record = self.recorder.record_from_result(
            result, action_type=action_type, parameters=parameters,
            user_id=user_id, user_session_id=session_id)
        return result, record

    # ── Undo (ownership-checked) ──────────────────────────────────────────────
    def undo_action(self, action_id: str, user_id: Optional[str] = None) -> bool:
        record = next((r for r in self.recorder.get_action_history()
                       if r.action_id == action_id), None)
        if record is None or not record.undoable or not record.undo_token:
            return False
        if record.user_id is not None and record.user_id != user_id:
            return False                                       # not the owner — refuse
        plugin = self.get_plugin(record.tool_name)
        if plugin is None:
            return False
        if plugin.undo(record.undo_token):
            self.recorder.mark_undone(action_id)
            return True
        return False
