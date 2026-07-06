"""Proactivity routes — poll the Layer-6 outreach queue (single-user).

No push channel without a frontend, so a client polls this for the current top candidates; the
scheduler's proactive-check job keeps the queue prioritized and pruned.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import ProactiveItemOut
from infra.db.proactive_store import PostgresProactiveQueue

router = APIRouter(prefix="/proactive", tags=["proactive"])


@router.get("", response_model=list[ProactiveItemOut])
def list_proactive(limit: int = 5, state=Depends(get_state)):
    try:
        items = PostgresProactiveQueue(state.session_factory, state.default_user_id).load(
            statuses=["pending", "deferred"])
    except Exception:
        raise HTTPException(status_code=503, detail="proactive queue unavailable")
    items.sort(key=lambda i: getattr(i, "current_priority", 0.0), reverse=True)
    return [ProactiveItemOut(
        item_id=i.item_id, item_type=i.item_type, status=i.status,
        content_basis=getattr(i, "content_basis", "") or "",
        current_priority=float(getattr(i, "current_priority", 0.0) or 0.0)) for i in items[:limit]]
