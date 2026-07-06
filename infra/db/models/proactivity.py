from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class ProactiveItem(UserScopedMixin, Base):
    """A queued Layer-6 outreach candidate (payload = serialized Layer-6 ProactiveItem)."""
    __tablename__ = "proactive_item"
    item_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    item_type: Mapped[str] = mapped_column(String(48), index=True, default="thread_follow_up")
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    payload: Mapped[dict] = mapped_column(_JSONB)
