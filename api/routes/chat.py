"""Chat endpoints — drive a conversation turn through the orchestrator.

`POST /chat` returns the finished turn as JSON; `POST /chat/stream` returns it as Server-Sent Events
(paced token delivery via Layer 9). Both are sync `def` on purpose: FastAPI runs them in a worker
thread, so the assembly's async->sync bridge (`_run`) is safe (no running event loop in this thread).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.layer9_output.stream_typing_overlay import StreamTypingOverlay
from api.dependencies import get_state, get_orchestrator
from api.schemas import ChatRequest, ChatResponse, EchoOut
from api.session_resolver import resolve_session_id
from api.streaming import stream_turn

logger = logging.getLogger("nova.api")
router = APIRouter(tags=["chat"])

# Fields ChatRequest carries beyond message/session_id -- Layer 1 SC-2's real, additive client
# signals (see api/schemas.py). The web client fills them in from `frontend/lib/chat/typingSignals.ts`.
_CLIENT_METADATA_FIELDS = (
    "user_typing_started_at", "deletion_occurred", "deletion_count",
    "peak_draft_length_chars", "final_draft_length_chars", "is_burst", "burst_count",
    "is_reply_to_proactive")


def _client_metadata(req: ChatRequest) -> dict:
    return {f: getattr(req, f) for f in _CLIENT_METADATA_FIELDS}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, state=Depends(get_state),
         orchestrator=Depends(get_orchestrator)) -> ChatResponse:
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=422, detail="message must not be empty")
    session_id = resolve_session_id(state, req.session_id)
    try:
        out = orchestrator.run_turn(state.default_user_id, req.message, session_id=session_id,
                                    client_metadata=_client_metadata(req))
    except Exception:
        logger.exception("turn failed")
        raise HTTPException(status_code=503, detail="conversation temporarily unavailable")
    tier = getattr(out, "crisis_tier", None)
    from api.echoes import project_echoes
    echoes = [EchoOut(**e) for e in project_echoes(getattr(out, "recalled_memories", []))]
    return ChatResponse(
        response=out.response_text,
        conversation_mode=getattr(out, "conversation_mode", "casual"),
        cognitive_system=getattr(out, "cognitive_system", "system1"),
        crisis_active=getattr(out, "crisis_active", False),
        crisis_tier=str(tier) if tier is not None else None,
        refined=getattr(out, "refined", False),
        tool_invoked=getattr(out, "tool_invoked", False),
        confabulation_guard=getattr(out, "confabulation_guard", False),
        echoes=echoes,
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
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=422, detail="message must not be empty")
    session_id = resolve_session_id(state, req.session_id)
    gen = stream_turn(orchestrator, StreamTypingOverlay(), state.default_user_id, req.message,
                      session_id=session_id, client_metadata=_client_metadata(req))
    return StreamingResponse(gen, media_type="text/event-stream",
                             headers={"X-Session-Id": session_id, "Cache-Control": "no-cache"})
