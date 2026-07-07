"""Conversation log routes — the permanent thread + annotations (single-user).

`GET /messages` is the transcript the /chat UI loads (newest-first, paginated by `before`); search is
keyword + date. Bookmarks and milestones are per-message annotations (the vision docs' long-press
"Bookmark" / "Make Milestone"). All user-scoped.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import BookmarkIn, EchoOut, MessageOut, MilestoneIn
from infra.db.message_store import PostgresMessageStore

router = APIRouter(tags=["messages"])


def _store(state):
    return PostgresMessageStore(state.session_factory, state.default_user_id)


def _iso(v):
    return v.isoformat() if v is not None and hasattr(v, "isoformat") else None


def _out(d: dict) -> MessageOut:
    return MessageOut(
        message_id=d["message_id"], cursor=d.get("row_id", 0), role=d["role"], content=d["content"],
        created_at=_iso(d.get("created_at")), session_key=d.get("session_key", "") or "",
        conversation_mode=d.get("mode"), crisis_active=bool(d.get("crisis_active")),
        tool_invoked=bool(d.get("tool_invoked")),
        echoes=[EchoOut(summary=e.get("summary", ""), when=e.get("when"),
                        created_at=e.get("created_at")) for e in (d.get("echoes") or [])],
        bookmarked=bool(d.get("bookmarked")), bookmark_category=d.get("bookmark_category"),
        is_milestone=bool(d.get("is_milestone")), milestone_label=d.get("milestone_label"))


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"invalid datetime: {s!r}")


@router.get("/messages", response_model=list[MessageOut])
def list_messages(limit: int = 50, before: Optional[int] = None, state=Depends(get_state)):
    try:
        return [_out(d) for d in _store(state).history(limit=limit, before_id=before)]
    except Exception:
        raise HTTPException(status_code=503, detail="messages temporarily unavailable")


@router.get("/messages/search", response_model=list[MessageOut])
def search_messages(q: str = "", start: Optional[str] = None, end: Optional[str] = None,
                    limit: int = 50, state=Depends(get_state)):
    try:
        rows = _store(state).search(query=q, start=_parse_dt(start), end=_parse_dt(end), limit=limit)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="search temporarily unavailable")
    return [_out(d) for d in rows]


@router.post("/messages/{message_id}/bookmark", response_model=MessageOut)
def bookmark_message(message_id: str, body: BookmarkIn, state=Depends(get_state)):
    st = _store(state)
    if not st.set_bookmark(message_id, True, category=body.category):
        raise HTTPException(status_code=404, detail="message not found")
    return _out(st.get(message_id))


@router.delete("/messages/{message_id}/bookmark", response_model=MessageOut)
def unbookmark_message(message_id: str, state=Depends(get_state)):
    st = _store(state)
    if not st.set_bookmark(message_id, False):
        raise HTTPException(status_code=404, detail="message not found")
    return _out(st.get(message_id))


@router.get("/bookmarks", response_model=list[MessageOut])
def list_bookmarks(category: Optional[str] = None, state=Depends(get_state)):
    return [_out(d) for d in _store(state).list_bookmarks(category=category)]


@router.post("/messages/{message_id}/milestone", response_model=MessageOut)
def make_milestone(message_id: str, body: MilestoneIn, state=Depends(get_state)):
    st = _store(state)
    if not st.set_milestone(message_id, True, label=body.label):
        raise HTTPException(status_code=404, detail="message not found")
    return _out(st.get(message_id))


@router.delete("/messages/{message_id}/milestone", response_model=MessageOut)
def unmake_milestone(message_id: str, state=Depends(get_state)):
    st = _store(state)
    if not st.set_milestone(message_id, False):
        raise HTTPException(status_code=404, detail="message not found")
    return _out(st.get(message_id))


@router.get("/milestones", response_model=list[MessageOut])
def list_milestones(state=Depends(get_state)):
    return [_out(d) for d in _store(state).list_milestones()]
