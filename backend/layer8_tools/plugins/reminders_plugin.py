"""Reminders plugin (architecture doc §9.4).

Lightweight timeline reminders (not a task manager). Every operation is AUTO — reminders are
local, low-stakes, and fully reversible — and delete archives for undo. A real OS/calendar
backend can be injected; default is in-memory.
"""

from __future__ import annotations

import uuid

from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.schemas import (
    ActionType,
    Capability,
    ConfirmationTier,
    ToolOutcome,
    ToolResult,
)


class RemindersPlugin(ToolPlugin):
    name = "reminders"

    def __init__(self) -> None:
        self._reminders: dict[str, dict] = {}
        self._archived: dict[str, dict] = {}
        self._undo_log: dict[str, str] = {}  # token -> reminder_id (restore)

    def capabilities(self) -> list[Capability]:
        return [
            Capability("create_reminder", ActionType.CREATE.value, "Create a reminder",
                       default_tier=ConfirmationTier.AUTO.value, reversible=True,
                       required_params=["text", "due"]),
            Capability("list_reminders", ActionType.READ.value, "List reminders",
                       default_tier=ConfirmationTier.AUTO.value),
            Capability("complete_reminder", ActionType.UPDATE.value, "Mark a reminder done",
                       default_tier=ConfirmationTier.AUTO.value, required_params=["reminder_id"]),
            Capability("snooze_reminder", ActionType.UPDATE.value, "Snooze a reminder",
                       default_tier=ConfirmationTier.AUTO.value,
                       required_params=["reminder_id", "duration"]),
            Capability("delete_reminder", ActionType.DELETE.value, "Delete a reminder",
                       default_tier=ConfirmationTier.AUTO.value, reversible=True,
                       required_params=["reminder_id"]),
        ]

    def execute(self, operation: str, parameters: dict) -> ToolResult:
        parameters = parameters or {}
        if operation == "create_reminder":
            return self._create(parameters)
        if operation == "list_reminders":
            return ToolResult(self.name, "list_reminders", ToolOutcome.SUCCESS.value,
                              data=list(self._reminders.values()))
        if operation == "complete_reminder":
            return self._set_flag(parameters, "completed", True, "completed")
        if operation == "snooze_reminder":
            return self._snooze(parameters)
        if operation == "delete_reminder":
            return self._delete(parameters)
        return ToolResult(self.name, operation, ToolOutcome.FAILURE.value,
                          error_message=f"unsupported operation: {operation}")

    def _create(self, params: dict) -> ToolResult:
        reminder_id = uuid.uuid4().hex
        self._reminders[reminder_id] = {
            "reminder_id": reminder_id, "text": params["text"], "due": params["due"],
            "recurrence": params.get("recurrence"), "completed": False,
        }
        token = uuid.uuid4().hex
        self._undo_log[token] = reminder_id
        return ToolResult(self.name, "create_reminder", ToolOutcome.SUCCESS.value,
                          result_summary="Reminder created", data=self._reminders[reminder_id],
                          undo_token=token)

    def _set_flag(self, params: dict, key: str, value, verb: str) -> ToolResult:
        reminder = self._reminders.get(params["reminder_id"])
        if reminder is None:
            return ToolResult(self.name, f"{verb}_reminder", ToolOutcome.FAILURE.value,
                              error_message="reminder not found")
        reminder[key] = value
        return ToolResult(self.name, f"{verb}_reminder", ToolOutcome.SUCCESS.value,
                          result_summary=f"Reminder {verb}", data=reminder)

    def _snooze(self, params: dict) -> ToolResult:
        reminder = self._reminders.get(params["reminder_id"])
        if reminder is None:
            return ToolResult(self.name, "snooze_reminder", ToolOutcome.FAILURE.value,
                              error_message="reminder not found")
        reminder["snoozed_by"] = params["duration"]
        return ToolResult(self.name, "snooze_reminder", ToolOutcome.SUCCESS.value,
                          result_summary="Reminder snoozed", data=reminder)

    def _delete(self, params: dict) -> ToolResult:
        reminder_id = params["reminder_id"]
        reminder = self._reminders.pop(reminder_id, None)
        if reminder is None:
            return ToolResult(self.name, "delete_reminder", ToolOutcome.FAILURE.value,
                              error_message="reminder not found")
        self._archived[reminder_id] = reminder
        token = uuid.uuid4().hex
        self._undo_log[token] = reminder_id
        return ToolResult(self.name, "delete_reminder", ToolOutcome.SUCCESS.value,
                          result_summary="Reminder deleted", data={"reminder_id": reminder_id},
                          undo_token=token)

    def undo(self, undo_token: str) -> bool:
        reminder_id = self._undo_log.pop(undo_token, None)
        if reminder_id is None:
            return False
        archived = self._archived.pop(reminder_id, None)
        if archived is not None:           # undo a delete → restore
            self._reminders[reminder_id] = archived
            return True
        return self._reminders.pop(reminder_id, None) is not None  # undo a create → remove
