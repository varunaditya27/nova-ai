"""Postgres-backed conversation message log — the single permanent thread.

Persists every turn-half (user + nova) so the chat UI can load history, search, and annotate. One
user-scoped thread; ordering + pagination is by the monotonic row ``id`` (stable, gap-free cursor).
Returns plain dicts (messages have no backend domain type); the API projects them to ``MessageOut``.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func

import infra.db.models as m
from infra.db.engine import session_scope


def _row_to_dict(r) -> dict:
    payload = dict(r.payload or {})
    return {
        "row_id": r.id, "message_id": r.message_id, "session_key": r.session_key,
        "role": r.role, "content": r.content, "created_at": r.created_at,
        "bookmarked": r.bookmarked, "is_milestone": r.is_milestone,
        "echoes": list(payload.get("echoes", [])),
        "bookmark_category": payload.get("bookmark_category"),
        "milestone_label": payload.get("milestone_label"),
        "mode": payload.get("mode"), "cognitive_system": payload.get("cognitive_system"),
        "crisis_active": payload.get("crisis_active", False),
        "tool_invoked": payload.get("tool_invoked", False),
    }


class PostgresMessageStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._uid = str(user_id)

    def append(self, role: str, content: str, *, session_key: str = "",
               created_at: Optional[datetime] = None, echoes=None, **meta) -> str:
        message_id = uuid.uuid4().hex
        payload = {k: v for k, v in meta.items() if v is not None}
        if echoes:
            payload["echoes"] = list(echoes)
        with session_scope(self._sf) as s:
            row = m.ConversationMessage(
                user_id=self._uid, message_id=message_id, session_key=str(session_key or ""),
                role=role, content=content or "", payload=payload)
            if created_at is not None:
                row.created_at = created_at
            s.add(row)
        return message_id

    def history(self, limit: int = 50, before_id: Optional[int] = None) -> list[dict]:
        """Newest-first page; pass the oldest ``row_id`` you have as ``before_id`` to page back."""
        with session_scope(self._sf) as s:
            q = s.query(m.ConversationMessage).filter_by(user_id=self._uid)
            if before_id is not None:
                q = q.filter(m.ConversationMessage.id < before_id)
            rows = q.order_by(m.ConversationMessage.id.desc()).limit(max(1, min(limit, 200))).all()
            return [_row_to_dict(r) for r in rows]

    def search(self, query: str = "", start: Optional[datetime] = None,
               end: Optional[datetime] = None, limit: int = 50) -> list[dict]:
        with session_scope(self._sf) as s:
            q = s.query(m.ConversationMessage).filter_by(user_id=self._uid)
            if query:
                q = q.filter(m.ConversationMessage.content.ilike(f"%{query}%"))
            if start is not None:
                q = q.filter(m.ConversationMessage.created_at >= start)
            if end is not None:
                q = q.filter(m.ConversationMessage.created_at <= end)
            rows = q.order_by(m.ConversationMessage.id.desc()).limit(max(1, min(limit, 200))).all()
            return [_row_to_dict(r) for r in rows]

    def get(self, message_id: str) -> Optional[dict]:
        with session_scope(self._sf) as s:
            r = s.query(m.ConversationMessage).filter_by(
                user_id=self._uid, message_id=message_id).one_or_none()
            return _row_to_dict(r) if r is not None else None

    def _set_flag(self, message_id: str, *, bookmarked=None, is_milestone=None,
                  category=None, label=None) -> bool:
        with session_scope(self._sf) as s:
            r = s.query(m.ConversationMessage).filter_by(
                user_id=self._uid, message_id=message_id).one_or_none()
            if r is None:
                return False
            payload = dict(r.payload or {})
            if bookmarked is not None:
                r.bookmarked = bookmarked
                payload["bookmark_category"] = category if bookmarked else None
            if is_milestone is not None:
                r.is_milestone = is_milestone
                payload["milestone_label"] = label if is_milestone else None
            r.payload = payload
            return True

    def set_bookmark(self, message_id: str, bookmarked: bool, category: Optional[str] = None) -> bool:
        return self._set_flag(message_id, bookmarked=bookmarked, category=category)

    def set_milestone(self, message_id: str, is_milestone: bool, label: Optional[str] = None) -> bool:
        return self._set_flag(message_id, is_milestone=is_milestone, label=label)

    def list_bookmarks(self, category: Optional[str] = None, limit: int = 100) -> list[dict]:
        with session_scope(self._sf) as s:
            q = s.query(m.ConversationMessage).filter_by(user_id=self._uid, bookmarked=True)
            rows = q.order_by(m.ConversationMessage.id.desc()).limit(limit).all()
            out = [_row_to_dict(r) for r in rows]
        return [d for d in out if category is None or d["bookmark_category"] == category]

    def list_milestones(self, limit: int = 100) -> list[dict]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.ConversationMessage)
                    .filter_by(user_id=self._uid, is_milestone=True)
                    .order_by(m.ConversationMessage.id.asc()).limit(limit).all())
            return [_row_to_dict(r) for r in rows]

    def count(self) -> int:
        with session_scope(self._sf) as s:
            return s.query(m.ConversationMessage).filter_by(user_id=self._uid).count()

    def first(self) -> Optional[dict]:
        with session_scope(self._sf) as s:
            r = (s.query(m.ConversationMessage).filter_by(user_id=self._uid)
                 .order_by(m.ConversationMessage.id.asc()).first())
            return _row_to_dict(r) if r is not None else None

    def last_interaction_at(self) -> Optional[datetime]:
        with session_scope(self._sf) as s:
            r = (s.query(m.ConversationMessage).filter_by(user_id=self._uid)
                 .order_by(m.ConversationMessage.id.desc()).first())
            return r.created_at if r is not None else None

    def day_activity(self, start: datetime, end: datetime) -> dict[str, int]:
        """Message count per ISO date (for the calendar heatmap), user-scoped."""
        with session_scope(self._sf) as s:
            rows = (s.query(func.date(m.ConversationMessage.created_at), func.count())
                    .filter(m.ConversationMessage.user_id == self._uid,
                            m.ConversationMessage.created_at >= start,
                            m.ConversationMessage.created_at <= end)
                    .group_by(func.date(m.ConversationMessage.created_at)).all())
            return {str(d): int(c) for d, c in rows}
