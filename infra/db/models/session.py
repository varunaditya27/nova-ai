from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class Session(UserScopedMixin, Base):
    __tablename__ = "session"
    session_key: Mapped[str] = mapped_column(String(64), unique=True)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    # Real server-side latency signal source (Layer 1 SC-2, ClientMetadata.nova_last_delivered_at)
    # -- when Nova's response for this session's previous turn was delivered, stamped by the
    # post-turn state writer and read back by perceive() on the next turn.
    last_delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                    nullable=True)
