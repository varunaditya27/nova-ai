"""Sessions routes — read-only list of the user's sessions (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import infra.db.models as models
from api.dependencies import get_state
from api.schemas import SessionOut
from infra.db.engine import session_scope

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(state=Depends(get_state)):
    try:
        with session_scope(state.session_factory) as s:
            rows = s.query(models.Session).filter_by(user_id=state.default_user_id).all()
            return [SessionOut(session_key=r.session_key, turn_count=r.turn_count) for r in rows]
    except Exception:
        raise HTTPException(status_code=503, detail="sessions temporarily unavailable")
