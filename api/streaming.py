"""SSE streaming of a completed conversation turn (paced by Layer-9's typing overlay).

Streaming here is *paced delivery of the finished, guardrailed response*, not token-from-LLM
streaming: Nova's invariant is that Layer 11 SC-1 runs post-generation, before Layer 9 delivers, so
raw model tokens must never reach the user un-vetted. ``stream_turn`` runs the full orchestrator turn
(crisis veto + SC-1 + all post-turn writes, exactly like ``POST /chat``), then replays the delivered
text as ``StreamTypingOverlay``-paced token events. The overlay's own contract: "the full response is
available; the UI renders tokens with these delays."

Wire protocol (``text/event-stream``): one ``meta`` frame, then one ``token`` frame per token
(``{token, delay_ms}``; concatenating the tokens reconstructs the response exactly), then ``done``.
"""
from __future__ import annotations

import json
import logging
import random as _random
import re
from datetime import datetime, timezone
from typing import Iterator, Optional

logger = logging.getLogger("nova.api")

# Layer-3 conversation modes -> Layer-9 StreamTypingOverlay pacing modes.
_MODE_TO_TYPING = {
    "casual": "casual_chat",
    "emotional_support": "emotional_support",
    "crisis": "crisis_support",
    "celebration": "celebration",
    "technical_discussion": "technical",
    "goal_planning": "deep_reasoning",
    "life_review": "deep_reasoning",
    "social_coaching": "emotional_support",
}
_DEFAULT_TYPING_MODE = "casual_chat"


def _circadian_band(now: datetime) -> str:
    """Coarse hour->band for the overlay's delay modulation (late_night slower, morning faster)."""
    h = now.hour
    if h < 5:
        return "late_night"
    if h < 8:
        return "early_morning"
    if h < 12:
        return "morning"
    if h >= 23:
        return "late_night"
    return "afternoon"


def _tokenize(text: str) -> list[str]:
    """Whitespace-preserving tokens: each word carries its trailing whitespace; concatenation is
    lossless so the client can reconstruct the exact delivered text."""
    return re.findall(r"\S+\s*|\s+", text)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def stream_turn(orchestrator, overlay, user_id: str, message: str, *, session_id: str = "",
                now: Optional[datetime] = None, rng=_random) -> Iterator[str]:
    """Run a full turn, then yield SSE frames (meta -> token* -> done) with overlay-paced delays."""
    now = now or datetime.now(timezone.utc)
    try:
        out = orchestrator.run_turn(user_id, message, now=now, session_id=session_id)

        mode = getattr(out, "conversation_mode", "casual")
        typing_mode = _MODE_TO_TYPING.get(mode, _DEFAULT_TYPING_MODE)
        band = _circadian_band(now)

        yield _sse("meta", {
            "session_id": session_id,
            "conversation_mode": mode,
            "cognitive_system": getattr(out, "cognitive_system", "system1"),
            "crisis_active": getattr(out, "crisis_active", False),
            "refined": getattr(out, "refined", False),
            "confabulation_guard": getattr(out, "confabulation_guard", False),
        })

        text = getattr(out, "delivered", None) or getattr(out, "response_text", "") or ""
        prev = ""
        for token in _tokenize(text):
            events = overlay.emit_token(token, prev, typing_mode, band, rng=rng)
            delay = sum(getattr(e, "delay_before_ms", 0) for e in events)
            yield _sse("token", {"token": token, "delay_ms": int(delay)})
            prev = token

        yield _sse("done", {
            "session_id": session_id,
            "conversation_mode": mode,
            "cognitive_system": getattr(out, "cognitive_system", "system1"),
            "crisis_active": getattr(out, "crisis_active", False),
            "refined": getattr(out, "refined", False),
        })
    except Exception:
        # The turn itself is defensive (the orchestrator degrades rather than raising), so this is
        # a last-resort guard for a failure in streaming/pacing: emit a terminal error frame so the
        # client gets a clean, handleable signal instead of a silently truncated stream.
        logger.exception("stream_turn failed; emitting error frame")
        yield _sse("error", {"session_id": session_id,
                             "message": "stream interrupted; please retry"})
