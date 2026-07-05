from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class SyncDelta(UserScopedMixin, Base):
    """Zero-knowledge sync row: the server stores opaque AES ciphertext + routing metadata only.
    ``id`` (from the mixin) is the monotonic pull cursor; the server never decrypts ``payload``."""
    __tablename__ = "sync_delta"
    delta_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_device: Mapped[str] = mapped_column(String(64), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[str] = mapped_column(Text)          # opaque AES ciphertext
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
