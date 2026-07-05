from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class Goal(UserScopedMixin, Base):
    __tablename__ = "goal"
    goal_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="tentative")
    payload: Mapped[dict] = mapped_column(_JSONB)
