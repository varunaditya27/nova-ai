from __future__ import annotations

from sqlalchemy import Boolean, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import TimestampMixin, UserScopedMixin

# Real JSONB in Postgres; TEXT-backed JSON on SQLite (keeps the offline suite dependency-free).
_JSONB = JSON().with_variant(JSONB, "postgresql")


class EpisodicMemory(UserScopedMixin, Base):
    __tablename__ = "episodic_memory"
    memory_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Chroma link (later)
    payload: Mapped[dict] = mapped_column(_JSONB)


class SemanticMemory(UserScopedMixin, Base):
    __tablename__ = "semantic_memory"
    memory_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)


class IdentityMemory(TimestampMixin, Base):
    __tablename__ = "identity_memory"
    belief_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(_JSONB)


class UserWorldModel(UserScopedMixin, Base):
    __tablename__ = "user_world_model"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_world_model_user_id"),)
    payload: Mapped[dict] = mapped_column(_JSONB)


class NarrativeChain(UserScopedMixin, Base):
    __tablename__ = "narrative_chain"
    chain_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)


class MemoryAudit(UserScopedMixin, Base):
    __tablename__ = "memory_audit"
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)
