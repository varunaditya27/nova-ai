"""Postgres-backed Layer-2 memory store — a drop-in for InMemoryMemoryStore.

Rich Layer-2 memory dataclasses are round-tripped through a JSONB ``payload`` column via
``memory_serde``; a few promoted, indexed columns carry the fields the read path filters on.
Every method opens a short-lived ``session_scope``; ORM rows never escape the store (callers
only ever see reconstructed dataclasses).
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from backend.layer2_memory.memory_store import resolve_uwm_query
from backend.layer2_memory.schemas import (
    EpisodicMemory, IdentityMemory, Memory, SemanticMemory, UserWorldModel,
)
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresMemoryStore:
    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    # ── Episodic ─────────────────────────────────────────────────────────
    def save_episodic(self, memory: EpisodicMemory) -> UUID:
        with session_scope(self._sf) as s:
            row = s.query(m.EpisodicMemory).filter_by(memory_id=str(memory.memory_id)).one_or_none()
            if row is None:
                s.add(m.EpisodicMemory(
                    user_id=str(memory.user_id), memory_id=str(memory.memory_id),
                    is_deleted=memory.is_deleted, is_archived=memory.is_archived,
                    payload=to_jsonable(memory)))
            else:
                row.user_id = str(memory.user_id)
                row.is_deleted = memory.is_deleted
                row.is_archived = memory.is_archived
                row.payload = to_jsonable(memory)
        return memory.memory_id

    def get_episodic(self, memory_id: UUID) -> Optional[EpisodicMemory]:
        with session_scope(self._sf) as s:
            row = s.query(m.EpisodicMemory).filter_by(memory_id=str(memory_id)).one_or_none()
            return from_jsonable(EpisodicMemory, row.payload) if row else None

    def all_episodic(self, user_id) -> list[EpisodicMemory]:
        with session_scope(self._sf) as s:
            rows = s.query(m.EpisodicMemory).filter_by(user_id=str(user_id)).all()
            return [from_jsonable(EpisodicMemory, r.payload) for r in rows]

    def active_episodic(self, user_id) -> list[EpisodicMemory]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.EpisodicMemory)
                    .filter_by(user_id=str(user_id), is_deleted=False, is_archived=False).all())
            return [from_jsonable(EpisodicMemory, r.payload) for r in rows]

    # ── Semantic ─────────────────────────────────────────────────────────
    def save_semantic(self, memory: SemanticMemory) -> UUID:
        with session_scope(self._sf) as s:
            row = s.query(m.SemanticMemory).filter_by(memory_id=str(memory.memory_id)).one_or_none()
            if row is None:
                s.add(m.SemanticMemory(
                    user_id=str(memory.user_id), memory_id=str(memory.memory_id),
                    is_deprecated=memory.is_deprecated, payload=to_jsonable(memory)))
            else:
                row.user_id = str(memory.user_id)
                row.is_deprecated = memory.is_deprecated
                row.payload = to_jsonable(memory)
        return memory.memory_id

    def active_semantic(self, user_id) -> list[SemanticMemory]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.SemanticMemory)
                    .filter_by(user_id=str(user_id), is_deprecated=False).all())
            return [from_jsonable(SemanticMemory, r.payload) for r in rows]

    # ── Identity (cross-user) ────────────────────────────────────────────
    def save_identity(self, belief: IdentityMemory) -> UUID:
        with session_scope(self._sf) as s:
            row = s.query(m.IdentityMemory).filter_by(belief_id=str(belief.belief_id)).one_or_none()
            if row is None:
                s.add(m.IdentityMemory(
                    belief_id=str(belief.belief_id), is_immutable=belief.is_immutable,
                    payload=to_jsonable(belief)))
            else:
                row.is_immutable = belief.is_immutable
                row.payload = to_jsonable(belief)
        return belief.belief_id

    def identity_beliefs(self) -> list[IdentityMemory]:
        with session_scope(self._sf) as s:
            rows = s.query(m.IdentityMemory).all()
            return [from_jsonable(IdentityMemory, r.payload) for r in rows]

    # ── Recall candidates ────────────────────────────────────────────────
    def candidate_memories(self, user_id) -> list[Memory]:
        return [*self.active_episodic(user_id), *self.active_semantic(user_id)]

    # ── User World Model ─────────────────────────────────────────────────
    def save_uwm(self, uwm: UserWorldModel) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.UserWorldModel).filter_by(user_id=str(uwm.user_id)).one_or_none()
            if row is None:
                s.add(m.UserWorldModel(user_id=str(uwm.user_id), payload=to_jsonable(uwm)))
            else:
                row.payload = to_jsonable(uwm)

    def load_uwm(self, user_id) -> Optional[UserWorldModel]:
        with session_scope(self._sf) as s:
            row = s.query(m.UserWorldModel).filter_by(user_id=str(user_id)).one_or_none()
            return from_jsonable(UserWorldModel, row.payload) if row else None

    def query_uwm(self, user_id, query_type: str, context: str = "") -> dict:
        return resolve_uwm_query(self.load_uwm(user_id), query_type, context)
