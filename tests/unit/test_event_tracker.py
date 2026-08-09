"""Tests for SC-2 Interpersonal Event Tracker (architecture doc §4)."""

from datetime import datetime

from backend.layer5_relationship import event_tracker as et
from backend.layer5_relationship.schemas import Recency, SocialEvent, SocialEventType

NOW = datetime(2026, 6, 28)


# ── Rule-based detection (§4.4 Pass 1) ───────────────────────────────────────
def test_detect_conflict_onset():
    hits = et.detect_events_rule_based("I had a fight with my sister yesterday")
    assert SocialEventType.CONFLICT_ONSET.value in [t for t, _ in hits]


def test_detect_support_withheld():
    hits = et.detect_events_rule_based("when I needed her, she wasn't there for me")
    assert SocialEventType.SUPPORT_WITHHELD.value in [t for t, _ in hits]


def test_detect_boundary_violation():
    hits = et.detect_events_rule_based("he completely crossed a line this time")
    assert SocialEventType.BOUNDARY_VIOLATION.value in [t for t, _ in hits]


def test_detect_reconnection():
    hits = et.detect_events_rule_based("we reconnected after not talking for months")
    assert SocialEventType.RECONNECTION.value in [t for t, _ in hits]


def test_detect_user_set_boundary():
    hits = et.detect_events_rule_based("I finally set a boundary with him")
    assert SocialEventType.USER_SET_BOUNDARY.value in [t for t, _ in hits]


def test_no_event_for_neutral_text():
    assert et.detect_events_rule_based("the weather is nice today") == []


# ── Event construction (§4.3) ────────────────────────────────────────────────
def test_extract_events_builds_social_event():
    events = et.extract_events("I had a fight with my sister", session_id="s1",
                               person_id="p1", now=NOW)
    assert len(events) >= 1
    ev = events[0]
    assert isinstance(ev, SocialEvent)
    assert ev.event_type == SocialEventType.CONFLICT_ONSET.value
    assert ev.person_id == "p1"
    assert ev.summary
    assert ev.event_valence < 0           # conflict is negative-valence
    assert ev.extraction_confidence > 0
    assert ev.reported_timestamp == NOW


def test_rule_based_summary_is_neutral_never_raw_text():
    # §10 Constraint 3: "summary ... never the raw conversation text" -- the rule-based pass used
    # to violate its own module's contract by storing a truncated, near-verbatim copy of the
    # message. A specific, identifying detail from the input must not survive into the summary.
    ev = et.extract_events(
        "I had a huge fight with my sister Priya about the inheritance money, "
        "it was really ugly", session_id="s1", person_id="p1", now=NOW)[0]
    assert "Priya" not in ev.summary
    assert "inheritance" not in ev.summary
    assert ev.summary == "Mentioned a conflict or falling-out with someone."


def test_extract_events_support_received_is_positive():
    events = et.extract_events("she really showed up for me when it mattered", now=NOW)
    assert events
    assert events[0].event_valence > 0


def test_extract_events_recency_defaults_to_current():
    events = et.extract_events("I had an argument with my roommate", now=NOW)
    assert events[0].recency == Recency.CURRENT.value


def test_extract_events_empty_text():
    assert et.extract_events("", now=NOW) == []


# ── LLM fallback (§4.4 Pass 2) ───────────────────────────────────────────────
def test_extract_events_uses_llm_when_rules_find_nothing():
    def fake_llm(prompt):
        return {"events": [{
            "person_reference": "my friend",
            "event_type": "drift",
            "summary": "Growing distance with a friend.",
            "user_perspective": "saddened",
            "event_valence": -0.4,
            "emotional_intensity": 0.5,
            "recency": "recent",
            "is_resolved": False,
            "extraction_confidence": 0.7,
        }]}

    events = et.extract_events("things feel different between us lately", now=NOW,
                               llm_fn=fake_llm)
    assert len(events) == 1
    assert events[0].event_type == SocialEventType.DRIFT.value
    assert events[0].recency == Recency.RECENT.value
    assert events[0].summary == "Growing distance with a friend."


def test_extract_events_llm_not_called_when_rules_match():
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        return {"events": []}

    et.extract_events("I had a fight with my sister", now=NOW, llm_fn=fake_llm)
    assert calls == []      # rule-based match → no LLM call on the live path
