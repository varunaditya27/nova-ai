"""Calendar plugin (architecture doc §9.1).

Unified calendar surface (Google / Apple / Outlook in production via an injected
``backend`` adapter; an in-memory store by default so it runs offline). Reads are AUTO,
create is SOFT, delete is HARD. Deletes are archived rather than dropped, so they undo.
"""

from __future__ import annotations

import uuid
from typing import Optional

from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.schemas import (
    ActionType,
    Capability,
    ConfirmationTier,
    RiskLevel,
    ToolOutcome,
    ToolResult,
)


class CalendarPlugin(ToolPlugin):
    name = "calendar"

    def __init__(self) -> None:
        self._events: dict[str, dict] = {}
        self._archived: dict[str, dict] = {}
        self._undo_log: dict[str, tuple[str, str]] = {}  # token -> (reverse_op, event_id)

    def capabilities(self) -> list[Capability]:
        return [
            Capability("create_event", ActionType.CREATE.value, "Create a calendar event",
                       default_tier=ConfirmationTier.SOFT.value, reversible=True,
                       external_impact=True, required_params=["title", "start"]),
            Capability("list_events", ActionType.READ.value, "List calendar events",
                       default_tier=ConfirmationTier.AUTO.value),
            Capability("find_free_time", ActionType.READ.value, "Find free time slots",
                       default_tier=ConfirmationTier.AUTO.value, required_params=["duration"]),
            Capability("delete_event", ActionType.DELETE.value, "Delete a calendar event",
                       default_tier=ConfirmationTier.HARD.value, reversible=True,
                       external_impact=True, risk_level=RiskLevel.MEDIUM.value,
                       required_params=["event_id"]),
        ]

    def execute(self, operation: str, parameters: dict) -> ToolResult:
        parameters = parameters or {}
        if operation == "create_event":
            return self._create_event(parameters)
        if operation == "list_events":
            return self._list_events(parameters)
        if operation == "find_free_time":
            return self._find_free_time(parameters)
        if operation == "delete_event":
            return self._delete_event(parameters)
        return ToolResult(self.name, operation, ToolOutcome.FAILURE.value,
                          error_message=f"unsupported operation: {operation}")

    def _create_event(self, params: dict) -> ToolResult:
        event_id = uuid.uuid4().hex
        self._events[event_id] = {
            "event_id": event_id,
            "title": params["title"],
            "start": params["start"],
            "duration": params.get("duration"),
            "description": params.get("description", ""),
        }
        token = uuid.uuid4().hex
        self._undo_log[token] = ("delete", event_id)
        return ToolResult(self.name, "create_event", ToolOutcome.SUCCESS.value,
                          result_summary=f"Created event '{params['title']}'",
                          data={"event_id": event_id}, undo_token=token)

    def _list_events(self, params: dict) -> ToolResult:
        events = list(self._events.values())
        return ToolResult(self.name, "list_events", ToolOutcome.SUCCESS.value,
                          result_summary=f"{len(events)} event(s)", data=events)

    def _find_free_time(self, params: dict) -> ToolResult:
        # Offline stub: with no real busy data, the requested duration is free.
        slots = [{"start": "open", "duration": params.get("duration")}]
        return ToolResult(self.name, "find_free_time", ToolOutcome.SUCCESS.value,
                          result_summary="1 free slot", data=slots)

    def _delete_event(self, params: dict) -> ToolResult:
        event_id = params["event_id"]
        event = self._events.pop(event_id, None)
        if event is None:
            return ToolResult(self.name, "delete_event", ToolOutcome.FAILURE.value,
                              error_message="event not found")
        self._archived[event_id] = event
        token = uuid.uuid4().hex
        self._undo_log[token] = ("restore", event_id)
        return ToolResult(self.name, "delete_event", ToolOutcome.SUCCESS.value,
                          result_summary="Event deleted", data={"event_id": event_id},
                          undo_token=token)

    def undo(self, undo_token: str) -> bool:
        entry = self._undo_log.pop(undo_token, None)
        if entry is None:
            return False
        reverse_op, event_id = entry
        if reverse_op == "delete":
            self._events.pop(event_id, None)
            return True
        if reverse_op == "restore":
            event = self._archived.pop(event_id, None)
            if event is None:
                return False
            self._events[event_id] = event
            return True
        return False
