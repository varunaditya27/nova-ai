from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class ToolAction(UserScopedMixin, Base):
    __tablename__ = "tool_action"
    tool: Mapped[str] = mapped_column(String(48))
    params: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(32), default="recorded")
