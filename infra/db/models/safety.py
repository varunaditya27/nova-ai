from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class SafetyEvent(UserScopedMixin, Base):
    __tablename__ = "safety_event"
    tier: Mapped[str] = mapped_column(String(16))
    detail: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
