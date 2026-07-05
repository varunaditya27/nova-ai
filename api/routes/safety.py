"""Safety routes — read-only recent crisis assessments (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import SafetyEventOut
from infra.db.safety_store import PostgresSafetyLog

router = APIRouter(prefix="/safety", tags=["safety"])


def _out(s) -> SafetyEventOut:
    detected = getattr(s, "detected_at", None)
    return SafetyEventOut(tier=s.tier, confidence=getattr(s, "confidence", 0.0),
                          detected_at=detected.isoformat() if detected else None,
                          signal_types=list(getattr(s, "signal_types", []) or []))


@router.get("/events", response_model=list[SafetyEventOut])
def list_safety_events(limit: int = 20, state=Depends(get_state)):
    try:
        events = PostgresSafetyLog(state.session_factory).recent(state.default_user_id, limit)
    except Exception:
        raise HTTPException(status_code=503, detail="safety log temporarily unavailable")
    return [_out(s) for s in events]
