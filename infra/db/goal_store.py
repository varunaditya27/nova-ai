"""Postgres-backed Layer-7 GoalStore — a drop-in for the in-memory GoalStore.

Overrides the persistence methods (JSONB payload via memory_serde) and inherits get_relevant_goals,
which is expressed purely in terms of load_by_status + pure scoring.
"""
from __future__ import annotations

from backend.layer7_goals.goal_store import GoalStore
from backend.layer7_goals.schemas import Goal
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresGoalStore(GoalStore):
    def __init__(self, session_factory, user_id) -> None:
        super().__init__()
        self._sf = session_factory
        self._user_id = str(user_id)

    def _upsert(self, goal: Goal) -> None:
        # This store is bound to one user: writes are always scoped to self._user_id, and any
        # client-supplied goal.user_id is overridden — never write or reassign another user's row.
        goal.user_id = self._user_id
        with session_scope(self._sf) as s:
            row = s.query(m.Goal).filter_by(
                goal_id=str(goal.goal_id), user_id=self._user_id).one_or_none()
            if row is None:
                s.add(m.Goal(user_id=self._user_id, goal_id=str(goal.goal_id),
                             status=goal.status, payload=to_jsonable(goal)))
            else:
                row.status = goal.status
                row.payload = to_jsonable(goal)

    def add_goal(self, goal: Goal) -> None:
        self._upsert(goal)

    def update_goal(self, goal: Goal) -> None:
        self._upsert(goal)

    def get(self, goal_id: str):
        with session_scope(self._sf) as s:
            row = s.query(m.Goal).filter_by(
                goal_id=str(goal_id), user_id=self._user_id).one_or_none()
            return from_jsonable(Goal, row.payload) if row else None

    def delete(self, goal_id: str) -> bool:
        # Scoped to this user — a goal_id belonging to another user is never touched.
        with session_scope(self._sf) as s:
            row = s.query(m.Goal).filter_by(
                goal_id=str(goal_id), user_id=self._user_id).one_or_none()
            if row is None:
                return False
            s.delete(row)
            return True

    def load_by_status(self, statuses):
        with session_scope(self._sf) as s:
            rows = (s.query(m.Goal)
                    .filter(m.Goal.user_id == self._user_id, m.Goal.status.in_(list(statuses)))
                    .all())
            return [from_jsonable(Goal, r.payload) for r in rows]
