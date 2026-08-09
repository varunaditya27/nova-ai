"""Proactivity routes — poll the Layer-6 outreach queue (single-user).

No push channel without a frontend, so a client polls this for the current top candidates; the
scheduler's proactive-check job keeps the queue prioritized, pruned, and (as of 2026-08-09)
message-generated. Candidates are gated server-side through the real SC-3 Timing & Delivery Gate
(``evaluate_timing_gate``) before being returned — a future frontend rendering ``content_basis``
directly as a Nova message can no longer bypass the gate's five block groups just by reading this
endpoint. ``message`` carries the real SC-4-generated text once the background job has produced
one; ``content_basis`` remains the internal fragment for debugging/inspection.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.dependencies import get_state
from api.proactive_delivery import build_timing_context, gate_passes
from api.schemas import ProactiveItemOut
from backend.layer6_proactivity.schemas import ItemStatus
from infra.db.proactive_store import PostgresProactiveQueue

logger = logging.getLogger("nova.api")
router = APIRouter(prefix="/proactive", tags=["proactive"])

_STREAM_POLL_SECONDS = 30
_STREAM_MAX_SECONDS = 25 * 60   # bounded connection lifetime; EventSource auto-reconnects


@router.get("", response_model=list[ProactiveItemOut])
def list_proactive(limit: int = 5, state=Depends(get_state)):
    uid = state.default_user_id
    now = datetime.now(timezone.utc)
    try:
        items = PostgresProactiveQueue(state.session_factory, uid).load(
            statuses=["pending", "deferred"])
        ctx = build_timing_context(state.session_factory, uid, now, state.config)
    except Exception:
        raise HTTPException(status_code=503, detail="proactive queue unavailable")

    approved = [i for i in items if gate_passes(i, ctx, now)]
    approved.sort(key=lambda i: getattr(i, "current_priority", 0.0), reverse=True)
    return [ProactiveItemOut(
        item_id=i.item_id, item_type=i.item_type, status=i.status,
        content_basis=getattr(i, "content_basis", "") or "",
        message=getattr(i, "generated_message", "") or "",
        current_priority=float(getattr(i, "current_priority", 0.0) or 0.0))
        for i in approved[:limit]]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream_gen(session_factory, uid: str, config: dict) -> Iterator[str]:
    """Push newly gate-passing, message-generated items as they clear the gate. Bounded lifetime
    (`_STREAM_MAX_SECONDS`) rather than truly indefinite -- a sync generator run in FastAPI's
    threadpool has no built-in client-disconnect detection, so this closes on its own and relies
    on `EventSource`'s native auto-reconnect (standard browser behavior) rather than holding a
    worker thread open forever. Single-user, local deployment: one open connection at a time."""
    seen: set[str] = set()
    started = time.monotonic()
    yield _sse("connected", {})
    while time.monotonic() - started < _STREAM_MAX_SECONDS:
        now = datetime.now(timezone.utc)
        try:
            items = PostgresProactiveQueue(session_factory, uid).load(
                statuses=["pending", "deferred"])
            ctx = build_timing_context(session_factory, uid, now, config)
            for i in items:
                if i.item_id in seen or not getattr(i, "generated_message", ""):
                    continue
                if gate_passes(i, ctx, now):
                    seen.add(i.item_id)
                    yield _sse("item", {
                        "item_id": i.item_id, "item_type": i.item_type,
                        "message": i.generated_message,
                        "current_priority": float(getattr(i, "current_priority", 0.0) or 0.0)})
        except Exception:
            logger.exception("proactive stream poll failed; continuing")
        yield _sse("heartbeat", {})
        time.sleep(_STREAM_POLL_SECONDS)


@router.get("/stream")
def stream_proactive(state=Depends(get_state)) -> StreamingResponse:
    """Push channel for real, gate-passing, SC-4-generated proactive messages — the piece
    `GET /proactive` (poll-only) never had. A client calls `POST /{item_id}/delivered` once it
    shows an `item` event to the user, closing the SC-5 response-tracking loop."""
    gen = _stream_gen(state.session_factory, state.default_user_id, state.config)
    return StreamingResponse(gen, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@router.post("/{item_id}/delivered")
def mark_delivered(item_id: str, state=Depends(get_state)):
    """SC-5 (§7): a client calls this the moment it actually shows a proactive item to the user
    (e.g. right after the SSE push), transitioning it to SENT so response tracking on the next
    /chat turn (``is_reply_to_proactive``) has a real, timestamped item to attribute a reply to."""
    q = PostgresProactiveQueue(state.session_factory, state.default_user_id)
    item = next((i for i in q.load() if i.item_id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="proactive item not found")
    item.status = ItemStatus.SENT.value
    item.sent_at = datetime.now(timezone.utc)
    q.upsert(item)
    return {"item_id": item_id, "status": item.status}
