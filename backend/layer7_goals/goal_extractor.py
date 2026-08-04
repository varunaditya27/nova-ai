"""SC-1 — Goal Extractor (architecture doc §3).

Detects when the user has expressed a meaningful intention — explicit or implicit — and
converts that natural-language statement into a structured goal. Goals are almost never
expressed in structured language, so extraction is LLM-driven, gated by a fast keyword
pre-filter and followed by semantic deduplication against existing goals.

The LLM is injected as ``llm_fn`` (returns a dict or JSON string) and the dedup embedding
comparison as ``similarity_fn`` (token-overlap default), so the component runs offline.
Per §10, extraction is asynchronous and failure-tolerant — any failure yields a
"no goal detected" result and never blocks response generation.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, Optional

from backend.layer7_goals.schemas import Goal, GoalExtractionResult

# Fast pre-filter keywords (architecture doc §3.3).
GOAL_SIGNAL_KEYWORDS = [
    # Explicit
    "want to", "trying to", "working on", "my goal", "i plan to",
    "i'm going to", "decided to", "i need to", "committed to",
    # Implicit
    "wish i could", "been meaning to", "always wanted", "someday",
    "keep putting off", "never get around to", "i should",
    # Progress updates
    "got further", "slipped up", "back on track", "gave up on",
    "finished", "completed", "hit my", "made progress",
]

_DUPLICATE_THRESHOLD = 0.82


def should_run_extractor(message: str) -> bool:
    """Cheap gate before the LLM extraction call (architecture doc §3.3)."""
    low = (message or "").lower()
    return any(kw in low for kw in GOAL_SIGNAL_KEYWORDS)


def _token_overlap(a: str, b: str) -> float:
    ta = {t.strip(".,!?'\"").lower() for t in a.split() if t.strip(".,!?'\"")}
    tb = {t.strip(".,!?'\"").lower() for t in b.split() if t.strip(".,!?'\"")}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def is_duplicate_goal(
    new_title: str,
    active_goals: list[Goal],
    similarity_fn: Optional[Callable[[str, str], float]] = None,
    threshold: float = _DUPLICATE_THRESHOLD,
) -> tuple[bool, Optional[str]]:
    """Check the candidate against existing goals (architecture doc §3.5)."""
    sim = similarity_fn or _token_overlap
    for goal in active_goals:
        if sim(new_title, goal.title) > threshold:
            return True, goal.goal_id
    return False, None


def build_extraction_prompt(
    user_message: str, prior_context: str, active_goal_summaries: str
) -> str:
    """Assemble the goal-extraction prompt (architecture doc §3.4)."""
    return (
        "SYSTEM:\nYou are a goal extraction specialist. Identify whether the user has "
        "expressed a meaningful personal intention, aspiration, or goal. A goal requires "
        "sustained effort over time; single-use tasks and undirected venting are NOT goals. "
        "Do not infer goals that are not present; if uncertain, set confidence < 0.6.\n\n"
        f"User message: {user_message}\n\n"
        f"Prior context (last 3 turns): {prior_context}\n\n"
        f"User's existing active goals (for deduplication): {active_goal_summaries}\n\n"
        "Return JSON with goal_detected, is_update, goal_id_if_update, update_type, "
        "update_description, and new_goal (raw_statement, inferred_title, inferred_domain, "
        "inferred_direction, has_explicit_deadline, deadline_description, has_explicit_metric, "
        "metric_description, emotional_weight, confidence, signal_strength)."
    )


def extract_goal(
    message: str,
    message_id: str = "",
    prior_context: str = "",
    active_goals: Optional[list[Goal]] = None,
    llm_fn: Optional[Callable[[str], object]] = None,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
    now: Optional[datetime] = None,
) -> GoalExtractionResult:
    """Detect/extract a goal from a message (architecture doc §3).

    Returns a not-detected result when the pre-filter fails, no ``llm_fn`` is supplied, or
    the LLM reports no goal. New goals are deduplicated against ``active_goals``; a duplicate
    is recorded as a reaffirmation (``was_duplicate=True``) rather than a new goal.
    """
    now = now or datetime.utcnow()
    active_goals = active_goals or []
    result = GoalExtractionResult(extraction_timestamp=now, message_id=message_id)

    if not should_run_extractor(message):
        return result
    if llm_fn is None:
        return result

    summaries = "; ".join(g.title for g in active_goals) or "(none)"
    prompt = build_extraction_prompt(message, prior_context, summaries)
    try:
        raw = llm_fn(prompt)
    except Exception:
        return result
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return result
    if not isinstance(raw, dict) or not raw.get("goal_detected"):
        return result

    result.goal_detected = True

    if raw.get("is_update"):
        result.is_update = True
        result.goal_id_if_update = raw.get("goal_id_if_update")
        result.update_type = raw.get("update_type")
        result.update_description = raw.get("update_description")
        return result

    new_goal = raw.get("new_goal") or {}
    result.confidence = float(new_goal.get("confidence", raw.get("confidence", 0.0)))
    result.signal_strength = str(new_goal.get("signal_strength", ""))

    title = new_goal.get("inferred_title", "")
    dup, matched = is_duplicate_goal(title, active_goals, similarity_fn)
    if dup:
        result.was_duplicate = True
        result.matched_goal_id = matched
        return result

    result.new_goal_data = new_goal
    return result
