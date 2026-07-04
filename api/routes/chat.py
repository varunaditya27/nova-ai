"""Chat endpoint — drives a single conversation turn through the orchestrator.

Sync `def` on purpose: FastAPI runs it in a worker thread, so the assembly's async->sync bridge
(`_run`) is safe (no running event loop in this thread). WebSocket streaming is a later increment.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state, get_orchestrator
from api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger("nova.api")
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, state=Depends(get_state),
         orchestrator=Depends(get_orchestrator)) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    try:
        out = orchestrator.run_turn(state.default_user_id, req.message, session_id=session_id)
    except Exception:
        logger.exception("turn failed")
        raise HTTPException(status_code=503, detail="conversation temporarily unavailable")
    return ChatResponse(
        response=out.response_text,
        conversation_mode=getattr(out, "conversation_mode", "casual"),
        cognitive_system=getattr(out, "cognitive_system", "system1"),
        crisis_active=getattr(out, "crisis_active", False),
        refined=getattr(out, "refined", False),
        session_id=session_id)
