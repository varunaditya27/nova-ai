from __future__ import annotations

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class SocialGraph(UserScopedMixin, Base):
    """One row per user — the whole Layer-5 SocialGraph (nodes + edges), like the UWM."""
    __tablename__ = "social_graph"
    __table_args__ = (UniqueConstraint("user_id", name="uq_social_graph_user_id"),)
    payload: Mapped[dict] = mapped_column(_JSONB)


class SocialEvent(UserScopedMixin, Base):
    """One row per detected interpersonal event, like EpisodicMemory."""
    __tablename__ = "social_event"
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    person_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)


class SocialPattern(UserScopedMixin, Base):
    """One row per detected social pattern (SC-3, batch-computed)."""
    __tablename__ = "social_pattern"
    pattern_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)
