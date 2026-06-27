"""In-memory memory store + UWM query interface (architecture doc §7.9, §11, §13).

The backing storage for episodic / semantic / identity memories and the User World Model.
Production persists these in SQLite + SQLCipher (on-device) with an hnswlib vector index;
this in-process implementation is the default behind the same interface, used in tests and
before a DB store is wired. The Memory Arbiter and State Updater are the only callers.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from .schemas import (
    EpisodicMemory,
    IdentityMemory,
    Memory,
    SemanticMemory,
    UserWorldModel,
)


class InMemoryMemoryStore:
    """Default in-process store for all Layer 2 persistent memory."""

    def __init__(self) -> None:
        self._episodic: dict[UUID, EpisodicMemory] = {}
        self._semantic: dict[UUID, SemanticMemory] = {}
        self._identity: dict[UUID, IdentityMemory] = {}
        self._uwm: dict[UUID, UserWorldModel] = {}

    # ── Episodic ─────────────────────────────────────────────────────────
    def save_episodic(self, memory: EpisodicMemory) -> UUID:
        self._episodic[memory.memory_id] = memory
        return memory.memory_id

    def get_episodic(self, memory_id: UUID) -> Optional[EpisodicMemory]:
        return self._episodic.get(memory_id)

    def all_episodic(self, user_id: UUID) -> list[EpisodicMemory]:
        return [m for m in self._episodic.values() if m.user_id == user_id]

    def active_episodic(self, user_id: UUID) -> list[EpisodicMemory]:
        return [
            m for m in self._episodic.values()
            if m.user_id == user_id and not m.is_deleted and not m.is_archived
        ]

    # ── Semantic ─────────────────────────────────────────────────────────
    def save_semantic(self, memory: SemanticMemory) -> UUID:
        self._semantic[memory.memory_id] = memory
        return memory.memory_id

    def active_semantic(self, user_id: UUID) -> list[SemanticMemory]:
        return [
            m for m in self._semantic.values()
            if m.user_id == user_id and not m.is_deprecated
        ]

    # ── Identity (Nova's self-model; not per-user) ───────────────────────
    def save_identity(self, belief: IdentityMemory) -> UUID:
        self._identity[belief.belief_id] = belief
        return belief.belief_id

    def identity_beliefs(self) -> list[IdentityMemory]:
        return list(self._identity.values())

    # ── Recall candidates ────────────────────────────────────────────────
    def candidate_memories(self, user_id: UUID) -> list[Memory]:
        """Active episodic + non-deprecated semantic memories eligible for recall."""
        return [*self.active_episodic(user_id), *self.active_semantic(user_id)]

    # ── User World Model ─────────────────────────────────────────────────
    def save_uwm(self, uwm: UserWorldModel) -> None:
        self._uwm[uwm.user_id] = uwm

    def load_uwm(self, user_id: UUID) -> Optional[UserWorldModel]:
        return self._uwm.get(user_id)

    def query_uwm(self, user_id: UUID, query_type: str, context: str = "") -> dict:
        """Typed UWM query interface (§7.9). Downstream layers never touch the UWM directly."""
        uwm = self._uwm.get(user_id)

        if query_type == "relationship_context":
            if uwm is None:
                return {"relevant_people": []}
            ctx = context.lower()
            people = [
                p for p in uwm.relationship_graph.people
                if p.name.lower() in ctx or any(a.lower() in ctx for a in p.aliases)
            ]
            return {"relevant_people": people}

        if query_type == "active_stressors":
            if uwm is None:
                return {"active_stressors": []}
            return {"active_stressors": uwm.life_context.active_stressors}

        if query_type == "communication_preferences":
            if uwm is None:
                return {"communication_preferences": None}
            return {"communication_preferences": uwm.communication_model}

        if query_type == "psychological_posture":
            if uwm is None:
                return {"support_style": None, "triggers": []}
            return {
                "support_style": uwm.psychological_model.preferred_support_style,
                "triggers": uwm.psychological_model.known_triggers,
            }

        if query_type == "life_stage_context":
            if uwm is None:
                return {"profile": None, "active_situations": []}
            return {
                "profile": uwm.profile,
                "active_situations": uwm.life_context.active_situations,
            }

        return {}  # pragma: no cover - unknown query type
