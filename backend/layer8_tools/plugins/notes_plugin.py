"""Notes plugin (architecture doc §9.3).

Capture-to-notes surface (Notion / Obsidian / markdown in production via an injected adapter;
in-memory by default). Because notes are private to the user and trivially reversible,
create/append are AUTO; delete is SOFT and archives rather than drops, so it undoes.
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


class NotesPlugin(ToolPlugin):
    name = "notes"

    def __init__(self) -> None:
        self._notes: dict[str, dict] = {}
        self._archived: dict[str, dict] = {}
        self._undo_log: dict[str, tuple[str, str]] = {}  # token -> (reverse_op, note_id)

    def capabilities(self) -> list[Capability]:
        return [
            Capability("create_note", ActionType.CREATE.value, "Create a note",
                       default_tier=ConfirmationTier.AUTO.value, reversible=True,
                       required_params=["content"]),
            Capability("append_to_note", ActionType.UPDATE.value, "Append to a note",
                       default_tier=ConfirmationTier.AUTO.value, reversible=True,
                       required_params=["note_id", "content"]),
            Capability("list_notes", ActionType.READ.value, "List notes",
                       default_tier=ConfirmationTier.AUTO.value),
            Capability("delete_note", ActionType.DELETE.value, "Delete a note",
                       default_tier=ConfirmationTier.SOFT.value, reversible=True,
                       required_params=["note_id"]),
        ]

    def execute(self, operation: str, parameters: dict) -> ToolResult:
        parameters = parameters or {}
        if operation == "create_note":
            return self._create(parameters)
        if operation == "append_to_note":
            return self._append(parameters)
        if operation == "list_notes":
            return ToolResult(self.name, "list_notes", ToolOutcome.SUCCESS.value,
                              data=list(self._notes.values()))
        if operation == "delete_note":
            return self._delete(parameters)
        return ToolResult(self.name, operation, ToolOutcome.FAILURE.value,
                          error_message=f"unsupported operation: {operation}")

    def _create(self, params: dict) -> ToolResult:
        note_id = uuid.uuid4().hex
        self._notes[note_id] = {
            "note_id": note_id, "title": params.get("title", ""),
            "content": params["content"], "tags": params.get("tags", []),
        }
        token = uuid.uuid4().hex
        self._undo_log[token] = ("delete", note_id)
        return ToolResult(self.name, "create_note", ToolOutcome.SUCCESS.value,
                          result_summary="Note created", data={"note_id": note_id},
                          undo_token=token)

    def _append(self, params: dict) -> ToolResult:
        note = self._notes.get(params["note_id"])
        if note is None:
            return ToolResult(self.name, "append_to_note", ToolOutcome.FAILURE.value,
                              error_message="note not found")
        note["content"] = f"{note['content']}\n{params['content']}"
        return ToolResult(self.name, "append_to_note", ToolOutcome.SUCCESS.value,
                          result_summary="Note appended", data={"note_id": note["note_id"]})

    def _delete(self, params: dict) -> ToolResult:
        note_id = params["note_id"]
        note = self._notes.pop(note_id, None)
        if note is None:
            return ToolResult(self.name, "delete_note", ToolOutcome.FAILURE.value,
                              error_message="note not found")
        self._archived[note_id] = note
        token = uuid.uuid4().hex
        self._undo_log[token] = ("restore", note_id)
        return ToolResult(self.name, "delete_note", ToolOutcome.SUCCESS.value,
                          result_summary="Note deleted", data={"note_id": note_id},
                          undo_token=token)

    def undo(self, undo_token: str) -> bool:
        entry = self._undo_log.pop(undo_token, None)
        if entry is None:
            return False
        reverse_op, note_id = entry
        if reverse_op == "delete":
            self._notes.pop(note_id, None)
            return True
        if reverse_op == "restore":
            note = self._archived.pop(note_id, None)
            if note is None:
                return False
            self._notes[note_id] = note
            return True
        return False
