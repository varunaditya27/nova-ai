from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class LongitudinalSummary(UserScopedMixin, Base):
    __tablename__ = "longitudinal_summary"
    period: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
