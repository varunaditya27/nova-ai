from __future__ import annotations

from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class OnboardingState(UserScopedMixin, Base):
    __tablename__ = "onboarding_state"
    cold_start_active: Mapped[bool] = mapped_column(Boolean, default=True)
    session_index: Mapped[int] = mapped_column(Integer, default=0)
