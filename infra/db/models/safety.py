from __future__ import annotations

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class SafetyEvent(UserScopedMixin, Base):
    __tablename__ = "safety_event"
    tier: Mapped[str] = mapped_column(String(16), index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(_JSONB)
