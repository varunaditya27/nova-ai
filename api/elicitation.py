"""Layer-13 per-turn active elicitation.

Picks at most one onboarding question to weave into a turn — only when a natural trigger fires in
the user's message, never front-loaded, never repeated. Maps the message (and session position) to
the natural-trigger tokens the ``ElicitationItem``s declare, then asks the ``ElicitationQueue`` for
the highest-priority surfaceable item. Already-asked inference targets and the current session are
supplied by the caller (persisted in the onboarding store) so nothing repeats and the early-period
one-question-per-session rate limit holds. Pure — no I/O.
"""
from __future__ import annotations

import re
from dataclasses import replace
from types import SimpleNamespace
from typing import Optional

from backend.layer13_onboarding.active_elicitation_queue import (
    INITIAL_ELICITATION_ITEMS, ElicitationQueue, ElicitationSurfacingPolicy)
from backend.layer13_onboarding.schemas import ElicitationItem

_SURFACING_POLICY = ElicitationSurfacingPolicy()

# Message content → the natural-trigger tokens the elicitation items declare (§4.3).
_TRIGGER_PATTERNS = {
    "user_says_hi_or_hello": r"\b(hi|hello|hey|heya|yo|good (morning|evening|afternoon))\b",
    "user_mentions_exams_or_studying":
        r"\b(exam|exams|study|studying|class|homework|assignment|college|university|semester)\b",
    "user_mentions_work_or_job": r"\b(work|working|job|office|boss|shift|career|client|coworker|colleague)\b",
    "user_mentions_a_schedule": r"\b(schedule|routine|calendar|deadline|my day|this week)\b",
    "user_mentions_stress": r"\b(stress|stressed|overwhelmed|burnt? out|exhausted|anxious|pressure)\b",
    "user_asks_about_productivity": r"\b(productiv|focus|get more done|time management)\b",
    "user_says_something_about_wanting_to_change":
        r"\b(want to change|need to change|turn things around|do better|start over)\b",
    "user_mentions_loneliness_or_isolation": r"\b(lonely|alone|isolated|no one to|by myself)\b",
    "user_mentions_needing_someone_to_talk_to":
        r"\b(someone to talk to|need to talk|vent|off my chest)\b",
    "user_mentions_wanting_to_do_something":
        r"\b(i want to|i'd like to|i wanna|hoping to|trying to|i've been meaning)\b",
    "user_mentions_a_plan": r"\b(my plan|i plan|planning|going to start|next month|this year)\b",
    "user_asks_for_advice_about_direction":
        r"\b(what should i|which way|not sure what to do|any advice)\b",
}

# Clear distress → raise the register so nice-to-have questions are suppressed this turn.
_DISTRESS = re.compile(
    r"\b(crying|hopeless|can'?t go on|worthless|hate myself|panic|terrified|devastated|grief|"
    r"breaking down|falling apart)\b", re.I)


def detect_triggers(message: str, session_number: int) -> set:
    """The natural-trigger tokens active for this message + session position."""
    low = (message or "").lower()
    fired = {name for name, pat in _TRIGGER_PATTERNS.items() if re.search(pat, low)}
    if session_number <= 1:
        fired.update({"any_first_personal_address_moment", "end_of_first_exchange"})
    if 2 <= session_number <= 3:
        fired.add("session_2_or_3_any_reflective_moment")
    return fired


def crude_emotional_intensity(message: str) -> float:
    """A lexical intensity estimate (Layer 3 hasn't run yet at cold-start time)."""
    return 0.85 if _DISTRESS.search(message or "") else 0.2


def select_elicitation(message: str, session_number: int, surfaced_targets,
                       asked_this_session: bool) -> Optional[ElicitationItem]:
    """The single ElicitationItem to surface this turn, or None (no trigger / already asked /
    rate-limited / inferred-only). Never returns an already-surfaced target.

    Two real gates from the module, not one reimplemented inline: next_surfaceable_item finds the
    highest-priority candidate whose trigger fired and (its own, looser) register check passes;
    ElicitationSurfacingPolicy.can_surface then re-checks all three real surfacing conditions
    (trigger, the FULLER two-tier register gate, and the session rate limit) before anything is
    actually asked — the same two-step sequence ColdStartEngine.on_message uses, previously
    reimplemented here as a single, looser inline check."""
    triggers = detect_triggers(message, session_number)
    if not triggers:
        return None

    surfaced = set(surfaced_targets or [])
    items = []
    for base in INITIAL_ELICITATION_ITEMS:
        it = replace(base)                               # copy — never mutate the module constant
        if it.inference_target in surfaced:
            it.status = "surfaced"                       # excluded from the waiting pool
        items.append(it)

    queue = ElicitationQueue(user_id="", items=items)
    intensity = crude_emotional_intensity(message)
    ctx = SimpleNamespace(active_triggers=triggers)
    item = queue.next_surfaceable_item(ctx, session_number, intensity, " ".join(triggers))
    if item is None or not item.question:                # inferred-only items are never asked aloud
        return None
    if not _SURFACING_POLICY.can_surface(
            item, ctx, session_number, intensity,
            elicitation_count_this_session=1 if asked_this_session else 0):
        return None
    return item
