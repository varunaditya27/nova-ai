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


class BehavioralPattern(UserScopedMixin, Base):
    """One row per detected Layer-10 behavioral pattern (SC-3, batch-computed), like SocialPattern."""
    __tablename__ = "longitudinal_pattern"
    pattern_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)


class LifeCalendarEntry(UserScopedMixin, Base):
    """One row per Layer-10 SC-5 calendar entry (relationship milestones, life-event anniversaries)."""
    __tablename__ = "life_calendar_entry"
    entry_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    has_fired: Mapped[bool] = mapped_column(default=False, index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)


class Retrospective(UserScopedMixin, Base):
    """One row per generated Layer-10 SC-4 retrospective packet."""
    __tablename__ = "retrospective"
    packet_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    has_been_surfaced: Mapped[bool] = mapped_column(default=False, index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)
