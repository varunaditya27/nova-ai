"""Postgres-backed Layer-8 ActionRecorder — durable, append-only tool-execution audit.

Drop-in subclass of the in-memory ``ActionRecorder``: keeps the parent's in-process dicts as a
write-through cache (so in-flight outcome/undo/link mutations work within a process), and also
persists every record to the ``tool_action`` table (payload = serialized ``ActionRecord`` via the
generic dataclass codec). ``get_action_history`` reads from the DB, so history survives restarts.
Bound to one user; all reads are user-scoped.
"""
from __future__ import annotations

from typing import Optional

import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import to_jsonable, from_jsonable
from backend.layer8_tools.action_recorder import ActionRecorder
from backend.layer8_tools.schemas import ActionRecord


class PostgresActionRecorder(ActionRecorder):
    def __init__(self, session_factory, user_id) -> None:
        super().__init__()
        self._sf = session_factory
        self._user_id = str(user_id)

    def _save(self, action: ActionRecord) -> None:
        action.user_id = action.user_id or self._user_id
        payload = to_jsonable(action)
        with session_scope(self._sf) as s:
            row = s.query(m.ToolAction).filter_by(action_id=action.action_id).one_or_none()
            if row is None:
                s.add(m.ToolAction(
                    user_id=action.user_id, action_id=action.action_id,
                    tool_name=action.tool_name, action_type=action.action_type,
                    outcome=action.outcome, payload=payload))
            else:
                row.outcome = action.outcome
                row.payload = payload

    # ── writes funnel through record_action (record_from_result calls it) ──────
    def record_action(self, action: ActionRecord) -> str:
        super().record_action(action)
        self._save(action)
        return action.action_id

    def record_action_outcome(self, action_id, outcome, result_summary="",
                              error_message=None) -> None:
        super().record_action_outcome(action_id, outcome, result_summary, error_message)
        rec = self._by_id.get(action_id)
        if rec is not None:
            self._save(rec)

    def link_to_episodic_memory(self, action_id, memory_id) -> None:
        super().link_to_episodic_memory(action_id, memory_id)
        rec = self._by_id.get(action_id)
        if rec is not None:
            self._save(rec)

    def mark_undone(self, action_id) -> None:
        super().mark_undone(action_id)
        rec = self._by_id.get(action_id)
        if rec is not None:
            self._save(rec)

    def get_action_history(self, user_id: Optional[str] = None,
                           tool_name: Optional[str] = None) -> list[ActionRecord]:
        uid = str(user_id) if user_id is not None else self._user_id
        with session_scope(self._sf) as s:
            q = s.query(m.ToolAction).filter_by(user_id=uid)
            if tool_name is not None:
                q = q.filter_by(tool_name=tool_name)
            rows = q.order_by(m.ToolAction.id.desc()).all()
            return [from_jsonable(ActionRecord, dict(r.payload)) for r in rows]
