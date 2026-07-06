from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class LongitudinalSummary(UserScopedMixin, Base):
    """A Layer-10 longitudinal artifact — weekly summary or narrative chapter (payload = serialized)."""
    __tablename__ = "longitudinal_summary"
    summary_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    period: Mapped[str] = mapped_column(String(32), index=True, default="weekly")
    payload: Mapped[dict] = mapped_column(_JSONB)
