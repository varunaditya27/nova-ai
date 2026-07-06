from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class RelationshipState(UserScopedMixin, Base):
    """Per-user Layer-4/5 relationship state (payload = serialized Layer-4 RelationshipState)."""
    __tablename__ = "relationship_state"
    stage: Mapped[str] = mapped_column(String(32), index=True, default="new")
    payload: Mapped[dict] = mapped_column(_JSONB)
