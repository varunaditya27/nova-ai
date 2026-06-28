"""SC: Tool Manager (architecture doc §5) — the Layer 8 orchestrator.

Sequences the full tool-use workflow for one message:

    detect intent → resolve missing params → confirmation gate → execute → record

The manager never performs actions itself; it routes to plugins through the uniform
``ToolPlugin`` interface, which makes them swappable. High-risk operations are gated: a SOFT
or HARD tier short-circuits with a ``ConfirmationRequest`` and only executes once ``confirmed``.
A missing required parameter short-circuits with a single clarification question. Intent
detection is an injected ``intent_fn`` (an LLM in production) with a keyword fallback so the
layer works offline.
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer8_tools import confirmation_gate, parameter_resolver
from backend.layer8_tools.action_recorder import ActionRecorder
from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.schemas import (
    ActionType,
    ToolIntent,
    ToolOutcome,
    ToolResult,
    ToolUseOutput,
)

# Keyword → (tool, operation) fallback when no intent_fn is supplied.
_KEYWORD_RULES = [
    (("search", "look up", "google", "find online"), "web_search", "search"),
    (("remind me", "reminder", "remind"), "reminders", "create_reminder"),
    (("send email", "email", "send a mail"), "email", "draft"),
    (("schedule", "calendar", "add event", "meeting", "appointment"), "calendar", "create_event"),
    (("take a note", "make a note", "jot down", "write down", "note that"), "notes", "create_note"),
]


class ToolManager:
    def __init__(
        self,
        recorder: Optional[ActionRecorder] = None,
        intent_fn: Optional[Callable[[str], object]] = None,
    ) -> None:
        self.recorder = recorder or ActionRecorder()
        self._intent_fn = intent_fn
        self._plugins: dict[str, ToolPlugin] = {}

    # ── Registration / routing ────────────────────────────────────────────────
    def register_plugin(self, plugin: ToolPlugin) -> None:
        self._plugins[plugin.name] = plugin

    def get_plugin(self, tool_name: str) -> Optional[ToolPlugin]:
        return self._plugins.get(tool_name)

    # ── Intent detection ──────────────────────────────────────────────────────
    def detect_intent(self, message: str) -> Optional[ToolIntent]:
        if self._intent_fn is not None:
            raw = self._intent_fn(message)
            return self._coerce_intent(raw)
        return self._keyword_intent(message or "")

    @staticmethod
    def _coerce_intent(raw) -> Optional[ToolIntent]:
        if raw is None or isinstance(raw, ToolIntent):
            return raw
        if isinstance(raw, dict) and raw.get("tool_name"):
            return ToolIntent(
                tool_name=raw["tool_name"], operation=raw.get("operation", ""),
                action_type=raw.get("action_type", ActionType.READ.value),
                parameters=raw.get("parameters", {}), confidence=raw.get("confidence", 0.0),
                raw_text=raw.get("raw_text", ""))
        return None

    def _keyword_intent(self, message: str) -> Optional[ToolIntent]:
        low = message.lower()
        for keywords, tool, operation in _KEYWORD_RULES:
            for kw in keywords:
                if kw in low:
                    params = {}
                    if tool == "web_search":
                        params = {"query": self._extract_query(low, message)}
                    return ToolIntent(tool_name=tool, operation=operation, parameters=params,
                                      confidence=0.5, raw_text=message)
        return None

    @staticmethod
    def _extract_query(low: str, message: str) -> str:
        for marker in ("search for ", "look up ", "search "):
            if marker in low:
                return message[low.index(marker) + len(marker):].strip()
        return message.strip()

    # ── Full per-message orchestration ────────────────────────────────────────
    def process(
        self, message: str, user_id: Optional[str] = None, confirmed: bool = False,
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

        # 2) Confirmation gate → SOFT/HARD short-circuits unless already confirmed.
        tier = confirmation_gate.compute_confirmation_tier(
            cap.action_type, reversible=cap.reversible, external_impact=cap.external_impact,
            risk_level=cap.risk_level, base_tier=cap.default_tier)
        if confirmation_gate.requires_user_confirmation(tier) and not confirmed:
            req = confirmation_gate.get_confirmation_request(
                intent.tool_name, cap.action_type, self._describe(intent, cap), tier,
                cap.risk_level, cap.reversible, intent.parameters)
            return ToolUseOutput(tool_invoked=False, intent=intent, confirmation_request=req)

        # 3) Execute + record.
        result, record = self._execute_and_record(
            plugin, intent.operation, intent.parameters, cap.action_type, user_id, session_id)
        return ToolUseOutput(tool_invoked=True, intent=intent, result=result, action_record=record)

    @staticmethod
    def _describe(intent: ToolIntent, cap) -> str:
        detail = ", ".join(f"{k}={v}" for k, v in (intent.parameters or {}).items())
        base = cap.description or f"{intent.tool_name} {intent.operation}"
        return f"{base} ({detail})" if detail else base

    # ── Direct execution ──────────────────────────────────────────────────────
    def execute_tool(
        self, tool_name: str, operation: str, parameters: dict,
        user_id: Optional[str] = None, session_id: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> ToolResult:
        plugin = self.get_plugin(tool_name)
        if plugin is None or not plugin.supports(operation):
            return ToolResult(tool_name, operation, ToolOutcome.FAILURE.value,
                              error_message=f"no plugin for {tool_name}.{operation}")
        cap = plugin.capability_for(operation)
        validation = plugin.validate_parameters(operation, parameters)
        if not validation.valid:
            result = ToolResult(tool_name, operation, ToolOutcome.FAILURE.value,
                                error_message="; ".join(validation.errors))
            self.recorder.record_from_result(
                result, action_type=cap.action_type, parameters=parameters,
                user_id=user_id, user_session_id=session_id)
            return result
        result, _ = self._execute_and_record(
            plugin, operation, parameters, action_type or cap.action_type, user_id, session_id)
        return result

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

    # ── Undo ──────────────────────────────────────────────────────────────────
    def undo_action(self, action_id: str) -> bool:
        record = next((r for r in self.recorder.get_action_history()
                       if r.action_id == action_id), None)
        if record is None or not record.undoable or not record.undo_token:
            return False
        plugin = self.get_plugin(record.tool_name)
        if plugin is None:
            return False
        if plugin.undo(record.undo_token):
            self.recorder.mark_undone(action_id)
            return True
        return False
