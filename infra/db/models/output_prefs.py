from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class OutputPref(UserScopedMixin, Base):
    __tablename__ = "output_pref"
    channel: Mapped[str] = mapped_column(String(32), default="text")
    voice: Mapped[str | None] = mapped_column(String(48), nullable=True)
