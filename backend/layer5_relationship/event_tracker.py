"""SC-2 — Interpersonal Event Tracker (architecture doc §4).

Detects, classifies, and structures *social events* — meaningful moments in the user's
relational world. Events are the raw material of pattern recognition (SC-3); without a
structured event log, SC-3 has nothing to analyze.

Two passes (§4.4): a fast, high-precision rule-based pass (regex) on the live path, and
an optional LLM extraction pass for ambiguous/complex events, run as a post-session
background process. The LLM is injected (``llm_fn``) so the layer runs offline; the rule
pass alone is fully deterministic.

Ethics (§10 Constraint 3): events store a neutral ``summary`` and ``user_perspective`` —
compressed extracted descriptions — never the raw conversation text.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Callable, Optional

from backend.layer5_relationship.schemas import (
    Recency,
    SocialEvent,
    SocialEventType,
)

# Rule-based detection table (architecture doc §4.4 Pass 1). Doc typos deduped.
EVENT_DETECTION_RULES: list[dict] = [
    {
        "patterns": [
            r"(fight|argument|confrontation|fell out|blow up|blew up) with",
            r"(angry at|upset with|not talking to|avoiding)",
            r"(we had a|there was a) (fight|disagreement|argument)",
        ],
        "event_type": SocialEventType.CONFLICT_ONSET.value,
        "min_confidence": 0.80,
    },
    {
        "patterns": [
            r"(didn't|did not|wouldn't) (support|help|show up|check in|respond)",
            r"(was not|wasn't|weren't) there for me",
            r"(expected|thought) (they|he|she) would (but|and)",
        ],
        "event_type": SocialEventType.SUPPORT_WITHHELD.value,
        "min_confidence": 0.72,
    },
    {
        "patterns": [
            r"(crossed a line|overstepped|invaded|violated|went through)",
            r"(didn't respect|ignored) (my|the) (boundary|space|limit|request)",
            r"(pressured|forced|guilted|manipulated) me",
        ],
        "event_type": SocialEventType.BOUNDARY_VIOLATION.value,
        "min_confidence": 0.75,
    },
    {
        "patterns": [
            r"(reached out|texted|called) (me|them|us)? ?(after|again)",
            r"(we) (caught up|reconnected|talked again|met up)",
            r"reconnected",
        ],
        "event_type": SocialEventType.RECONNECTION.value,
        "min_confidence": 0.78,
    },
    {
        "patterns": [
            r"(set|put) (a |my )?(boundary|limit|rule)",
            r"(told|said to) (them|him|her) (that|how|why) (I|it|this)",
            r"(made it clear|was clear) (that|about)",
        ],
        "event_type": SocialEventType.USER_SET_BOUNDARY.value,
        "min_confidence": 0.70,
    },
    {
        "patterns": [
            r"(was|were) there for me",
            r"(showed up|stuck around) for me",
            r"(supported|helped) me (through|with|a lot)",
        ],
        "event_type": SocialEventType.SUPPORT_RECEIVED.value,
        "min_confidence": 0.74,
    },
    {
        "patterns": [
            r"(made up|worked it out|patched things up|resolved (it|things))",
            r"(we're|we are) (good|okay|fine) (again|now)",
        ],
        "event_type": SocialEventType.CONFLICT_RESOLUTION.value,
        "min_confidence": 0.72,
    },
]

# Neutral, templated summaries for the rule-based pass (§10 Constraint 3: never raw text). Keyed
# to the seven event types EVENT_DETECTION_RULES can actually produce.
_NEUTRAL_SUMMARY: dict[str, str] = {
    SocialEventType.CONFLICT_ONSET.value: "Mentioned a conflict or falling-out with someone.",
    SocialEventType.SUPPORT_WITHHELD.value: "Mentioned someone not being there for them when expected.",
    SocialEventType.BOUNDARY_VIOLATION.value: "Mentioned someone crossing a boundary.",
    SocialEventType.RECONNECTION.value: "Mentioned reconnecting with someone.",
    SocialEventType.USER_SET_BOUNDARY.value: "Mentioned setting a boundary with someone.",
    SocialEventType.SUPPORT_RECEIVED.value: "Mentioned someone being supportive.",
    SocialEventType.CONFLICT_RESOLUTION.value: "Mentioned resolving a conflict with someone.",
}

# Valence hint by event type (architecture doc §4.3; sign drives SC-3/SC-4 reasoning).
_EVENT_VALENCE: dict[str, float] = {
    SocialEventType.CONFLICT_ONSET.value: -0.6,
    SocialEventType.CONFLICT_ESCALATION.value: -0.7,
    SocialEventType.CONFLICT_DEESCALATION.value: 0.3,
    SocialEventType.CONFLICT_RESOLUTION.value: 0.5,
    SocialEventType.CONFLICT_DORMANT.value: -0.2,
    SocialEventType.RECONNECTION.value: 0.5,
    SocialEventType.DEEPENING.value: 0.6,
    SocialEventType.DRIFT.value: -0.4,
    SocialEventType.RUPTURE.value: -0.8,
    SocialEventType.REPAIR.value: 0.6,
    SocialEventType.LIFE_MILESTONE_SHARED.value: 0.5,
    SocialEventType.ACHIEVEMENT_SHARED.value: 0.5,
    SocialEventType.LOSS_SHARED.value: -0.5,
    SocialEventType.BOUNDARY_VIOLATION.value: -0.6,
    SocialEventType.SUPPORT_RECEIVED.value: 0.6,
    SocialEventType.SUPPORT_WITHHELD.value: -0.6,
    SocialEventType.BETRAYAL.value: -0.8,
    SocialEventType.POSITIVE_SURPRISE.value: 0.6,
    SocialEventType.USER_SET_BOUNDARY.value: 0.4,
    SocialEventType.USER_AVOIDED_CONFLICT.value: -0.2,
    SocialEventType.USER_REACHED_OUT.value: 0.4,
    SocialEventType.USER_WITHDREW.value: -0.3,
}

_VALID_EVENT_TYPES = {e.value for e in SocialEventType}
_VALID_RECENCY = {r.value for r in Recency}


def detect_events_rule_based(text: str) -> list[tuple[str, float]]:
    """Fast regex detection of common social events (architecture doc §4.4 Pass 1)."""
    if not text:
        return []
    low = text.lower()
    hits: list[tuple[str, float]] = []
    seen: set[str] = set()
    for rule in EVENT_DETECTION_RULES:
        if rule["event_type"] in seen:
            continue
        for pattern in rule["patterns"]:
            if re.search(pattern, low):
                hits.append((rule["event_type"], rule["min_confidence"]))
                seen.add(rule["event_type"])
                break
    return hits


def _build_event(
    event_type: str,
    confidence: float,
    *,
    session_id: str,
    person_id: str,
    summary: str,
    user_perspective: str = "",
    recency: str = Recency.CURRENT.value,
    is_resolved: bool = False,
    emotional_intensity: float = 0.5,
    now: datetime,
    event_valence: Optional[float] = None,
) -> SocialEvent:
    valence = event_valence if event_valence is not None else _EVENT_VALENCE.get(event_type, 0.0)
    return SocialEvent(
        session_id=session_id,
        person_id=person_id,
        event_type=event_type,
        summary=summary,
        user_perspective=user_perspective,
        event_valence=valence,
        emotional_intensity=emotional_intensity,
        reported_timestamp=now,
        recency=recency if recency in _VALID_RECENCY else Recency.CURRENT.value,
        is_resolved=is_resolved,
        extraction_confidence=confidence,
    )


def _extract_events_llm(
    text: str,
    social_graph_brief: str,
    llm_fn: Callable[[str], object],
    *,
    session_id: str,
    person_id: str,
    now: datetime,
) -> list[SocialEvent]:
    """Parse structured events from an injected LLM (architecture doc §4.4 Pass 2)."""
    prompt = (
        "You are a social event extractor. Extract only events explicitly described — "
        "do not infer or speculate. Output valid JSON only.\n\n"
        f"CONVERSATION SUMMARY:\n{text}\n\n"
        f"KNOWN PEOPLE IN USER'S SOCIAL GRAPH:\n{social_graph_brief}\n"
    )
    try:
        result = llm_fn(prompt)
    except Exception:
        return []
    if isinstance(result, str):
        import json
        try:
            result = json.loads(result)
        except (ValueError, TypeError):
            return []
    if not isinstance(result, dict):
        return []

    events: list[SocialEvent] = []
    for raw in result.get("events", []):
        etype = raw.get("event_type")
        if etype not in _VALID_EVENT_TYPES:
            continue
        events.append(_build_event(
            etype, float(raw.get("extraction_confidence", 0.6)),
            session_id=session_id, person_id=person_id,
            summary=raw.get("summary", ""),
            user_perspective=raw.get("user_perspective", ""),
            recency=raw.get("recency", Recency.CURRENT.value),
            is_resolved=bool(raw.get("is_resolved", False)),
            emotional_intensity=float(raw.get("emotional_intensity", 0.5)),
            now=now,
            event_valence=raw.get("event_valence"),
        ))
    return events


def extract_events(
    text: str,
    session_id: str = "",
    person_id: str = "",
    social_graph_brief: str = "",
    recency: str = Recency.CURRENT.value,
    now: Optional[datetime] = None,
    llm_fn: Optional[Callable[[str], object]] = None,
) -> list[SocialEvent]:
    """Extract structured social events from text (architecture doc §4.4).

    Rule-based pass first; if it finds nothing and an ``llm_fn`` is supplied, the LLM
    extraction pass runs (the post-session background path). Returns ``[]`` for empty
    text. The summary is the neutral extracted text, never the raw input verbatim.
    """
    now = now or datetime.utcnow()
    if not text or not text.strip():
        return []

    hits = detect_events_rule_based(text)
    if hits:
        return [
            _build_event(
                etype, conf, session_id=session_id, person_id=person_id,
                summary=_NEUTRAL_SUMMARY.get(etype, "Mentioned a social event."),
                recency=recency, now=now,
            )
            for etype, conf in hits
        ]

    if llm_fn is not None:
        return _extract_events_llm(
            text, social_graph_brief, llm_fn,
            session_id=session_id, person_id=person_id, now=now,
        )
    return []
