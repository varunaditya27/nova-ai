from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class ToolAction(UserScopedMixin, Base):
    """Append-only audit row for one Layer-8 tool execution (payload = serialized ActionRecord)."""
    __tablename__ = "tool_action"
    action_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(48), index=True)
    action_type: Mapped[str] = mapped_column(String(16), index=True, default="read")
    outcome: Mapped[str] = mapped_column(String(16), index=True, default="success")
    payload: Mapped[dict] = mapped_column(_JSONB)
