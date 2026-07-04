from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import TimestampMixin, UserScopedMixin


class EpisodicMemory(UserScopedMixin, Base):
    __tablename__ = "episodic_memory"
    summary: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float, default=0.0)
    vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)


class SemanticMemory(UserScopedMixin, Base):
    __tablename__ = "semantic_memory"
    fact: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    support_count: Mapped[int] = mapped_column(Integer, default=1)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False)


class IdentityMemory(TimestampMixin, Base):
    __tablename__ = "identity_memory"
    key: Mapped[str] = mapped_column(String(128), index=True)
    value: Mapped[str] = mapped_column(Text)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False)


class MemoryAudit(UserScopedMixin, Base):
    __tablename__ = "memory_audit"
    event: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64))
