"""Longitudinal routes — read Layer-10 weekly summaries (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import LongitudinalSummaryOut
from infra.db.longitudinal_store import PostgresLongitudinalStore

router = APIRouter(prefix="/longitudinal", tags=["longitudinal"])


def _out(s) -> LongitudinalSummaryOut:
    def _iso(v):
        return v.isoformat() if v is not None and hasattr(v, "isoformat") else None
    return LongitudinalSummaryOut(
        summary_id=s.summary_id, week_start_date=_iso(getattr(s, "week_start_date", None)),
        week_end_date=_iso(getattr(s, "week_end_date", None)),
        session_count=getattr(s, "session_count", 0),
        dominant_theme=getattr(s, "dominant_theme", "") or "",
        week_narrative=getattr(s, "week_narrative", "") or "")


@router.get("/summaries", response_model=list[LongitudinalSummaryOut])
def list_summaries(limit: int = 10, state=Depends(get_state)):
    try:
        rows = PostgresLongitudinalStore(state.session_factory, state.default_user_id).summaries(
            period="weekly", limit=limit)
    except Exception:
        raise HTTPException(status_code=503, detail="longitudinal store unavailable")
    return [_out(s) for s in rows]


@router.get("/latest", response_model=LongitudinalSummaryOut)
def latest_summary(state=Depends(get_state)):
    latest = PostgresLongitudinalStore(state.session_factory, state.default_user_id).latest("weekly")
    if latest is None:
        raise HTTPException(status_code=404, detail="no summary yet")
    return _out(latest)
