"""Tests for the Layer 10 life-event extractor."""

from datetime import date, datetime, timezone

from backend.layer10_longitudinal import life_event_extractor as lee

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def test_should_run_extractor_on_a_major_transition_keyword():
    assert lee.should_run_extractor("I just started a new job on Monday") is True
    assert lee.should_run_extractor("we got married last weekend") is True


def test_should_not_run_extractor_on_a_neutral_message():
    assert lee.should_run_extractor("the weather is nice today") is False


def test_extract_no_keyword_returns_none():
    event = lee.extract_life_event("the sky is blue",
                                   llm_fn=lambda p: {"life_event_detected": True}, now=NOW)
    assert event is None


def test_extract_no_llm_returns_none():
    assert lee.extract_life_event("I started a new job", now=NOW) is None


def test_extract_detects_a_career_transition():
    def llm(prompt):
        return {
            "life_event_detected": True, "title": "started a new job",
            "category": "career_transition", "event_date": "2026-08-09",
            "significance_score": 0.8, "description": "began a new role", "confidence": 0.85,
        }
    event = lee.extract_life_event("I started a new job this week!", llm_fn=llm, now=NOW,
                                   user_id="u1")
    assert event is not None
    assert event.title == "started a new job"
    assert event.category == "career_transition"
    assert event.event_date == date(2026, 8, 9)
    assert event.user_id == "u1"
    assert event.significance_score == 0.8


def test_extract_below_confidence_threshold_returns_none():
    def llm(prompt):
        return {"life_event_detected": True, "title": "maybe a job", "confidence": 0.3}
    assert lee.extract_life_event("started a new job maybe", llm_fn=llm, now=NOW) is None


def test_extract_no_event_detected_returns_none():
    def llm(prompt):
        return {"life_event_detected": False}
    assert lee.extract_life_event("started a new job", llm_fn=llm, now=NOW) is None


def test_extract_invalid_category_falls_back_to_other():
    def llm(prompt):
        return {"life_event_detected": True, "title": "something big",
                "category": "not_a_real_category", "confidence": 0.9}
    event = lee.extract_life_event("started a new job", llm_fn=llm, now=NOW)
    assert event.category == "other"


def test_extract_invalid_date_falls_back_to_today():
    def llm(prompt):
        return {"life_event_detected": True, "title": "something big",
                "event_date": "not-a-date", "confidence": 0.9}
    event = lee.extract_life_event("started a new job", llm_fn=llm, now=NOW)
    assert event.event_date == NOW.date()


def test_extract_malformed_json_string_degrades_to_none():
    event = lee.extract_life_event("started a new job", llm_fn=lambda p: "not json", now=NOW)
    assert event is None


def test_extract_llm_exception_degrades_to_none():
    def broken(prompt):
        raise RuntimeError("llm unavailable")
    assert lee.extract_life_event("started a new job", llm_fn=broken, now=NOW) is None
