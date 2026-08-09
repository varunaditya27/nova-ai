from __future__ import annotations

from sqlalchemy import JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class FormatProfile(UserScopedMixin, Base):
    """One row per user — the whole Layer-9 UserFormatProfile, like the UWM/SocialGraph."""
    __tablename__ = "format_profile"
    __table_args__ = (UniqueConstraint("user_id", name="uq_format_profile_user_id"),)
    payload: Mapped[dict] = mapped_column(_JSONB)
