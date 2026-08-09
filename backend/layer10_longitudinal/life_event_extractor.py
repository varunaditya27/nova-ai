"""Life Event Extractor — the missing producer for Layer 10's chapter-boundary detection.

No detector exists for `LifeEvent` anywhere in this codebase (§3.4's `detect_chapter_boundaries`
has been callable but always fed `life_events=[]`, so no user's narrative ever gets a second
chapter). LLM-driven, gated by a fast keyword pre-filter, mirroring
`backend/layer1_input/thread_extractor.py`'s pattern (itself mirroring
`backend/layer7_goals/goal_extractor.py`) -- extraction is inherently a natural-language
judgment call ("did the user just describe a major life transition?"), not something a keyword
list alone can safely decide.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Callable, Optional

from backend.layer10_longitudinal.schemas import LifeEvent

# Fast pre-filter keywords -- major-transition language across the five real categories.
LIFE_EVENT_SIGNAL_KEYWORDS = [
    "started a new job", "got a new job", "got promoted", "was laid off", "got fired",
    "quit my job", "graduated", "started college", "started grad school", "dropped out",
    "got married", "got engaged", "we broke up", "got divorced", "we're expecting",
    "had a baby", "moved to", "moving to", "relocated", "new apartment", "bought a house",
    "passed away", "died", "lost my", "diagnosed with", "went into remission", "surgery",
]

_MIN_CONFIDENCE = 0.6
_VALID_CATEGORIES = {
    "career_transition", "educational_transition", "relational_major",
    "geographic_relocation", "major_loss", "health_major", "other",
}


def should_run_extractor(message: str) -> bool:
    """Cheap gate before the LLM extraction call."""
    low = (message or "").lower()
    return any(kw in low for kw in LIFE_EVENT_SIGNAL_KEYWORDS)


def build_extraction_prompt(user_message: str, today_label: str) -> str:
    """Assemble the life-event extraction prompt."""
    return (
        "SYSTEM:\nYou are a life-narrative specialist. Identify whether the user has just "
        "described a genuinely significant, chapter-defining life transition -- a career or "
        "educational change, a major relationship milestone, a geographic move, a major loss, "
        "or a major health event. Routine day-to-day events are NOT life events. Do not infer "
        "one that is not clearly present; if uncertain, set confidence < 0.6.\n\n"
        f"Today's date: {today_label}\n\n"
        f"User message: {user_message}\n\n"
        "Return JSON with life_event_detected, title (a short third-person label), category "
        "(one of career_transition, educational_transition, relational_major, "
        "geographic_relocation, major_loss, health_major, other), event_date (ISO date -- use "
        "today's date unless the message clearly places it in the past), significance_score "
        "(0-1), description (a short neutral summary), and confidence (0-1)."
    )


def extract_life_event(
    message: str,
    llm_fn: Optional[Callable[[str], object]] = None,
    now: Optional[datetime] = None,
    user_id: str = "",
) -> Optional[LifeEvent]:
    """Detect/extract a significant life event from a message, or ``None``.

    Returns ``None`` when the pre-filter fails, no ``llm_fn`` is supplied, the LLM reports no
    event, or confidence is below ``_MIN_CONFIDENCE`` -- failure-tolerant by construction, never
    blocks response generation (mirrors ``extract_thread``'s degradation contract).
    """
    now = now or datetime.utcnow()
    today = now.date() if isinstance(now, datetime) else now
    if not should_run_extractor(message):
        return None
    if llm_fn is None:
        return None

    prompt = build_extraction_prompt(message, today.isoformat())
    try:
        raw = llm_fn(prompt)
    except Exception:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    if not isinstance(raw, dict) or not raw.get("life_event_detected"):
        return None

    confidence = float(raw.get("confidence", 0.0) or 0.0)
    if confidence < _MIN_CONFIDENCE:
        return None

    title = str(raw.get("title") or "").strip()
    if not title:
        return None

    category = raw.get("category") if raw.get("category") in _VALID_CATEGORIES else "other"
    try:
        event_date = date.fromisoformat(str(raw.get("event_date")))
    except (TypeError, ValueError):
        event_date = today
    significance = max(0.0, min(1.0, float(raw.get("significance_score", 0.5) or 0.5)))

    return LifeEvent(
        event_id=uuid.uuid4().hex,
        user_id=user_id,
        title=title,
        category=category,
        event_date=event_date,
        significance_score=significance,
        detected_at=now if isinstance(now, datetime) else datetime.utcnow(),
        description=str(raw.get("description") or "") or None,
    )
