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

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.proactive_delivery import build_timing_context, gate_passes
from api.schemas import ProactiveItemOut
from backend.layer6_proactivity.schemas import ItemStatus
from infra.db.proactive_store import PostgresProactiveQueue

router = APIRouter(prefix="/proactive", tags=["proactive"])


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
