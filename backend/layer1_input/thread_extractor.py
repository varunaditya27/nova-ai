"""Narrative-Thread Extractor (architecture doc §3.5).

Detects when the user opens a conversational loop worth a future follow-up -- a scheduled event
("I have an interview Thursday"), an intention/commitment ("I'll call my mom back"), a chronic
situation, or a pending factual question -- and converts it into a ``NarrativeThread`` Layer 6
can later surface via ``on_thread_due``. Extraction is LLM-driven, gated by a fast keyword
pre-filter, mirroring ``backend/layer7_goals/goal_extractor.py``'s pattern (this module's own
docstring: thread *records* are created by the post-turn writer, not by ``perceive()`` itself).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.layer1_input.schemas import ImportanceTier, NarrativeThread, ThreadStatus, ThreadType

# Fast pre-filter keywords -- future-tense/commitment/pending-event language.
THREAD_SIGNAL_KEYWORDS = [
    "tomorrow", "next week", "next month", "this weekend", "later today", "tonight",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "i'll call", "i'll text", "i'll let you know", "i'll tell you", "remind me",
    "interview", "appointment", "surgery", "exam", "deadline", "meeting",
    "waiting to hear", "waiting on", "follow up", "check back", "results come",
]

_MIN_CONFIDENCE = 0.6
_VALID_TYPES = {t.value for t in ThreadType}
_VALID_TIERS = {t.value for t in ImportanceTier}


def should_run_extractor(message: str) -> bool:
    """Cheap gate before the LLM extraction call."""
    low = (message or "").lower()
    return any(kw in low for kw in THREAD_SIGNAL_KEYWORDS)


def build_extraction_prompt(user_message: str, now_label: str) -> str:
    """Assemble the thread-extraction prompt."""
    return (
        "SYSTEM:\nYou are a conversational continuity specialist. Identify whether the user "
        "has opened a loop worth Nova following up on later -- a scheduled future event, an "
        "intention or commitment they stated, a chronic ongoing situation, or a pending "
        "factual question awaiting an answer. Casual mentions with no future relevance are "
        "NOT threads. Do not infer a thread that is not present; if uncertain, set "
        "confidence < 0.6.\n\n"
        f"Current time: {now_label}\n\n"
        f"User message: {user_message}\n\n"
        "Return JSON with thread_detected, summary (a short third-person recap Nova can use "
        "to open the follow-up), thread_type (one of future_event, emotional_situation, "
        "intention_commitment, chronic_context, factual_pending), importance_tier (one of "
        "critical, high, medium, low), emotional_weight (0-1), follow_up_in_hours (a realistic "
        "number of hours from now to check back -- e.g. ~24-48 for a next-day event, ~4-12 for "
        "same-day, a few hundred for a next-week event), and confidence (0-1)."
    )


def extract_thread(
    message: str,
    llm_fn: Optional[Callable[[str], object]] = None,
    now: Optional[datetime] = None,
    source_session_id: Optional[str] = None,
) -> Optional[NarrativeThread]:
    """Detect/extract a narrative thread from a message, or ``None`` (architecture doc §3.5).

    Returns ``None`` when the pre-filter fails, no ``llm_fn`` is supplied, the LLM reports no
    thread, or confidence is below ``_MIN_CONFIDENCE`` -- failure-tolerant by construction, never
    blocks response generation (mirrors ``extract_goal``'s degradation contract).
    """
    now = now or datetime.utcnow()
    if not should_run_extractor(message):
        return None
    if llm_fn is None:
        return None

    prompt = build_extraction_prompt(message, now.isoformat())
    try:
        raw = llm_fn(prompt)
    except Exception:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    if not isinstance(raw, dict) or not raw.get("thread_detected"):
        return None

    confidence = float(raw.get("confidence", 0.0) or 0.0)
    if confidence < _MIN_CONFIDENCE:
        return None

    summary = str(raw.get("summary") or "").strip()
    if not summary:
        return None

    thread_type = raw.get("thread_type") if raw.get("thread_type") in _VALID_TYPES \
        else ThreadType.FACTUAL_PENDING.value
    importance_tier = raw.get("importance_tier") if raw.get("importance_tier") in _VALID_TIERS \
        else ImportanceTier.MEDIUM.value
    emotional_weight = max(0.0, min(1.0, float(raw.get("emotional_weight", 0.0) or 0.0)))
    try:
        follow_up_hours = max(0.5, float(raw.get("follow_up_in_hours", 24.0) or 24.0))
    except (TypeError, ValueError):
        follow_up_hours = 24.0

    return NarrativeThread(
        thread_id=uuid.uuid4(),
        summary=summary,
        created_at=now,
        follow_up_due_at=now + timedelta(hours=follow_up_hours),
        status=ThreadStatus.UNRESOLVED,
        emotional_weight=emotional_weight,
        importance_tier=ImportanceTier(importance_tier),
        thread_type=ThreadType(thread_type),
        source_session_id=source_session_id,
    )
