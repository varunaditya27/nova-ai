from __future__ import annotations

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class Goal(UserScopedMixin, Base):
    __tablename__ = "goal"
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="active")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
