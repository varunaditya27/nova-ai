"""SC-2 rule-based event detection tables (architecture doc §4.4 Pass 1, §4.3).

Split out of ``event_tracker.py``: static data, distinct from extraction logic.
"""

from __future__ import annotations

from backend.layer5_relationship.schemas import SocialEventType

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
NEUTRAL_SUMMARY: dict[str, str] = {
    SocialEventType.CONFLICT_ONSET.value: "Mentioned a conflict or falling-out with someone.",
    SocialEventType.SUPPORT_WITHHELD.value: "Mentioned someone not being there for them when expected.",
    SocialEventType.BOUNDARY_VIOLATION.value: "Mentioned someone crossing a boundary.",
    SocialEventType.RECONNECTION.value: "Mentioned reconnecting with someone.",
    SocialEventType.USER_SET_BOUNDARY.value: "Mentioned setting a boundary with someone.",
    SocialEventType.SUPPORT_RECEIVED.value: "Mentioned someone being supportive.",
    SocialEventType.CONFLICT_RESOLUTION.value: "Mentioned resolving a conflict with someone.",
}

# Valence hint by event type (architecture doc §4.3; sign drives SC-3/SC-4 reasoning).
EVENT_VALENCE: dict[str, float] = {
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
