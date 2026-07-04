from __future__ import annotations

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class RelationshipState(UserScopedMixin, Base):
    __tablename__ = "relationship_state"
    stage: Mapped[str] = mapped_column(String(32), default="new")
    trust: Mapped[float] = mapped_column(Float, default=0.0)
