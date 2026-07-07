from __future__ import annotations

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class ConversationMessage(UserScopedMixin, Base):
    """One turn-half of the single permanent conversation (role=user|nova).

    Promoted columns are the ones we query/sort/filter by (thread order, role, keyword search via
    `content`, and the bookmark/milestone annotation flags); everything else — turn metadata and the
    recalled-memory echoes — rides in the JSONB payload.
    """
    __tablename__ = "conversation_message"
    message_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    session_key: Mapped[str] = mapped_column(String(64), index=True, default="")
    role: Mapped[str] = mapped_column(String(16), index=True, default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    bookmarked: Mapped[bool] = mapped_column(Boolean, index=True, default=False)
    is_milestone: Mapped[bool] = mapped_column(Boolean, index=True, default=False)
    payload: Mapped[dict] = mapped_column(_JSONB, default=dict)
