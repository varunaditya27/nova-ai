"""SC-5 — Response Tracker (architecture doc §7).

Monitors what happens after a proactive message is sent. Two jobs: update the item's
lifecycle status and feed the response signal back into SC-1's queue priority model; and
classify the user's response within a 48-hour window.

Deterministic. Valence detection is a small keyword heuristic (the response itself is
re-routed through the full L1–L4 pipeline elsewhere; here we only need a coarse signal).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer6_proactivity.queue_manager import ProactiveQueueManager
from backend.layer6_proactivity.schemas import (
    ItemStatus,
    ProactiveItem,
    ResponseClassification,
    ResponseType,
)

RESPONSE_WINDOW_HOURS = 48
_POSITIVE_ENGAGEMENT_THRESHOLD = 0.6
_IGNORE_SUPPRESS_THRESHOLD = 3

_POSITIVE_WORDS = {"thanks", "thank", "great", "good", "yes", "yeah", "well", "happy",
                   "love", "appreciate", "glad", "awesome", "better"}
_NEGATIVE_WORDS = {"no", "not", "bad", "worse", "tired", "sad", "stressed", "hard",
                   "awful", "terrible", "sorry", "busy", "annoyed"}

_RESPONSIVENESS_WEIGHT = {
    ResponseType.IMMEDIATE.value: 1.0,
    ResponseType.QUICK.value: 0.8,
    ResponseType.SAME_DAY.value: 0.5,
    ResponseType.DELAYED.value: 0.3,
}


def _detect_valence(text: str) -> float:
    """Coarse keyword valence in [-1, 1] for engagement scoring."""
    tokens = {t.strip(".,!?'\"").lower() for t in text.split()}
    pos = len(tokens & _POSITIVE_WORDS)
    neg = len(tokens & _NEGATIVE_WORDS)
    if pos == neg:
        return 0.0
    return (pos - neg) / (pos + neg)


def compute_engagement_score(
    response_text: str, response_length: int, responsiveness: str, valence: float
) -> float:
    """Blend responsiveness, substance, and valence into a 0–1 engagement score (§7.2)."""
    speed = _RESPONSIVENESS_WEIGHT.get(responsiveness, 0.3)
    substance = min(1.0, response_length / 100.0)
    positivity = (valence + 1.0) / 2.0
    score = 0.5 * speed + 0.2 * substance + 0.3 * positivity
    return round(max(0.0, min(1.0, score)), 4)


def classify_response(
    send_timestamp: datetime,
    user_messages: list[tuple],
    now: Optional[datetime] = None,
) -> ResponseClassification:
    """Classify the first user message in the 48h window (architecture doc §7.2).

    ``user_messages`` is a list of ``(timestamp, text)`` tuples.
    """
    window_seconds = RESPONSE_WINDOW_HOURS * 3600
    in_window = sorted(
        [(ts, text) for ts, text in user_messages
         if 0 <= (ts - send_timestamp).total_seconds() < window_seconds],
        key=lambda m: m[0],
    )
    if not in_window:
        return ResponseClassification(responded=False, response_type=ResponseType.IGNORED.value,
                                      engagement_score=0.0)

    ts, text = in_window[0]
    hours = (ts - send_timestamp).total_seconds() / 3600
    if hours < 1:
        responsiveness = ResponseType.IMMEDIATE.value
    elif hours < 6:
        responsiveness = ResponseType.QUICK.value
    elif hours < 24:
        responsiveness = ResponseType.SAME_DAY.value
    else:
        responsiveness = ResponseType.DELAYED.value

    valence = _detect_valence(text)
    engagement = compute_engagement_score(text, len(text), responsiveness, valence)
    return ResponseClassification(
        responded=True,
        response_type=responsiveness,
        engagement_score=engagement,
        response_valence=valence,
    )


def update_queue_from_response(
    item: ProactiveItem,
    response: ResponseClassification,
    queue_manager: ProactiveQueueManager,
    user_preferences: dict,
) -> None:
    """Feed the response back into queue priority + preferences (architecture doc §7.3)."""
    pref_key = f"proactive_{item.item_type}_enabled"

    if response.responded:
        item.status = ItemStatus.RESPONDED.value
        item.user_response_valence = response.response_valence
        item.user_engaged = True
        if response.engagement_score > _POSITIVE_ENGAGEMENT_THRESHOLD:
            queue_manager.adjust_type_base_priority(
                item.item_type, +0.05, max_adjustment_total=0.15
            )
        user_preferences[pref_key] = True
        queue_manager.reset_ignore_count(item.item_type)
    else:
        item.status = ItemStatus.IGNORED.value
        item.user_engaged = False
        queue_manager.adjust_type_base_priority(
            item.item_type, -0.05, min_priority_floor=0.10
        )
        queue_manager.increment_ignore_count(item.item_type)
        if queue_manager.get_ignore_count(item.item_type) >= _IGNORE_SUPPRESS_THRESHOLD:
            user_preferences[pref_key] = False
