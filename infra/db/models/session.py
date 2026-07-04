from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class Session(UserScopedMixin, Base):
    __tablename__ = "session"
    session_key: Mapped[str] = mapped_column(String(64), unique=True)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
