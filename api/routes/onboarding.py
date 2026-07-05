"""Onboarding routes — read-only cold-start status (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import OnboardingOut
from infra.db.onboarding_store import PostgresOnboardingStore

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("", response_model=OnboardingOut)
def onboarding_status(state=Depends(get_state)):
    grad = state.config.get("onboarding", {}).get("graduation_sessions", 5)
    try:
        st = PostgresOnboardingStore(state.session_factory, state.default_user_id, grad).state()
    except Exception:
        raise HTTPException(status_code=503, detail="onboarding temporarily unavailable")
    return OnboardingOut(cold_start_active=st["cold_start_active"], session_index=st["session_index"])
