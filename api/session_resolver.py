"""Server-owned session boundaries for the single permanent thread.

The client's ``session_id`` is React state, so every page load minted a "new session" — and a tab
left open for weeks stayed one. Both distort what sessions drive: relationship stage (and with it
how freely Nova may reference the past), cold-start graduation, STM scope. A session is really a
stretch of conversation, so it ends after ``gap_minutes`` of silence, whichever tab sent it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from infra.db.message_store import PostgresMessageStore

DEFAULT_GAP_MINUTES = 30


def resolve_session_id(state, requested: str | None, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    gap = state.config.get("system", {}).get("session_gap_minutes", DEFAULT_GAP_MINUTES)
    last = PostgresMessageStore(state.session_factory, state.default_user_id).last_message_meta()
    if last is None:
        return requested or str(uuid.uuid4())
    last_at, last_key = last
    if last_at.tzinfo is None:                       # SQLite drops tz; stored values are UTC
        last_at = last_at.replace(tzinfo=timezone.utc)
    if last_key and now - last_at <= timedelta(minutes=gap):
        return last_key
    return str(uuid.uuid4())
