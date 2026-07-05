"""Chat endpoints — drive a conversation turn through the orchestrator.

`POST /chat` returns the finished turn as JSON; `POST /chat/stream` returns it as Server-Sent Events
(paced token delivery via Layer 9). Both are sync `def` on purpose: FastAPI runs them in a worker
thread, so the assembly's async->sync bridge (`_run`) is safe (no running event loop in this thread).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.layer9_output.stream_typing_overlay import StreamTypingOverlay
from api.dependencies import get_state, get_orchestrator
from api.schemas import ChatRequest, ChatResponse
from api.streaming import stream_turn

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


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, state=Depends(get_state),
                orchestrator=Depends(get_orchestrator)) -> StreamingResponse:
    """Stream the turn as Server-Sent Events (meta -> token* -> done).

    Sync generator on purpose: Starlette iterates it in the threadpool, so the assembly's
    async->sync bridge stays safe (no running event loop in that thread), same as ``POST /chat``.
    The full turn — crisis veto, SC-1 guardrails, and all post-turn writes — runs exactly as in
    ``/chat``; only delivery is paced (Layer 9 typing overlay). See ``api/streaming.py``.
    """
    session_id = req.session_id or str(uuid.uuid4())
    gen = stream_turn(orchestrator, StreamTypingOverlay(), state.default_user_id, req.message,
                      session_id=session_id)
    return StreamingResponse(gen, media_type="text/event-stream",
                             headers={"X-Session-Id": session_id, "Cache-Control": "no-cache"})
