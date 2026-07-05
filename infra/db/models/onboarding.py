from __future__ import annotations

from sqlalchemy import JSON, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class OnboardingState(UserScopedMixin, Base):
    __tablename__ = "onboarding_state"
    __table_args__ = (UniqueConstraint("user_id", name="uq_onboarding_state_user_id"),)
    cold_start_active: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(_JSONB)
