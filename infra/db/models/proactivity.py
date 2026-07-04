from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class ProactiveItem(UserScopedMixin, Base):
    __tablename__ = "proactive_item"
    kind: Mapped[str] = mapped_column(String(48))
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
