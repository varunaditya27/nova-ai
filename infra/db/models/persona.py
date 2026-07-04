from __future__ import annotations

from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class PersonaState(UserScopedMixin, Base):
    __tablename__ = "persona_state"
    warmth: Mapped[float] = mapped_column(Float, default=0.5)
    verbosity: Mapped[float] = mapped_column(Float, default=0.5)
    formality: Mapped[float] = mapped_column(Float, default=0.5)
