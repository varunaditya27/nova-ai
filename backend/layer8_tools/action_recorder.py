"""SC: Action Recorder (architecture doc §7).

The auditable log of every tool execution. It is **append-only**: records are added and their
lifecycle fields (outcome, linked memory, undone flag) are updated in place, but nothing is
ever removed — undoing an action is itself recorded, not erased. In production these rows
persist via ``infra.db.models.tools.ActionRecord`` and are inspectable through Layer 12; the
in-process store here keeps the layer testable offline.
"""

from __future__ import annotations

from typing import Optional

from backend.layer8_tools.schemas import (
    ActionRecord,
    ActionType,
    ToolOutcome,
    ToolResult,
)


class ActionRecorder:
    def __init__(self) -> None:
        self._records: list[ActionRecord] = []          # insertion order
        self._by_id: dict[str, ActionRecord] = {}

    def record_action(self, action: ActionRecord) -> str:
        """Append an ActionRecord and return its id (§7)."""
        self._records.append(action)
        self._by_id[action.action_id] = action
        return action.action_id

    def record_from_result(
        self,
        result: ToolResult,
        action_type: str = ActionType.READ.value,
        parameters: Optional[dict] = None,
        user_id: Optional[str] = None,
        user_session_id: Optional[str] = None,
    ) -> ActionRecord:
        """Build and append an ActionRecord from a plugin ToolResult."""
        record = ActionRecord(
            tool_name=result.tool_name, operation=result.operation, action_type=action_type,
            parameters=parameters or {}, outcome=result.outcome,
            result_summary=result.result_summary, error_message=result.error_message,
            user_id=user_id, user_session_id=user_session_id,
            undoable=result.undo_token is not None, undo_token=result.undo_token,
        )
        self.record_action(record)
        return record

    def record_action_outcome(
        self, action_id: str, outcome: str, result_summary: str = "",
        error_message: Optional[str] = None,
    ) -> None:
        """Update the lifecycle outcome of an existing record (§7)."""
        record = self._by_id.get(action_id)
        if record is None:
            return
        record.outcome = outcome
        if result_summary:
            record.result_summary = result_summary
        if error_message is not None:
            record.error_message = error_message

    def link_to_episodic_memory(self, action_id: str, memory_id: str) -> None:
        record = self._by_id.get(action_id)
        if record is not None:
            record.linked_episodic_memory_id = memory_id

    def mark_undone(self, action_id: str) -> None:
        """Flag a record as undone — recorded, never deleted (§7)."""
        record = self._by_id.get(action_id)
        if record is not None:
            record.undone = True

    def get_action_history(
        self, user_id: Optional[str] = None, tool_name: Optional[str] = None,
    ) -> list[ActionRecord]:
        """Return matching records, most recent first (§7)."""
        records = list(reversed(self._records))
        if user_id is not None:
            records = [r for r in records if r.user_id == user_id]
        if tool_name is not None:
            records = [r for r in records if r.tool_name == tool_name]
        return records
