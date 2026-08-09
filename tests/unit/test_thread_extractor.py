"""Tests for the narrative-thread extractor (architecture doc §3.5)."""

from datetime import datetime, timedelta, timezone

from backend.layer1_input import thread_extractor as te
from backend.layer1_input.schemas import ImportanceTier, ThreadStatus, ThreadType

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def test_should_run_extractor_on_future_event_keyword():
    assert te.should_run_extractor("I have an interview on Thursday") is True
    assert te.should_run_extractor("remind me to call the bank") is True


def test_should_not_run_extractor_on_neutral_message():
    assert te.should_run_extractor("the weather is nice today") is False


def test_extract_no_keyword_returns_none():
    thread = te.extract_thread("the sky is blue",
                               llm_fn=lambda p: {"thread_detected": True}, now=NOW)
    assert thread is None


def test_extract_no_llm_returns_none():
    thread = te.extract_thread("I have an interview on Thursday", now=NOW)
    assert thread is None


def test_extract_detects_a_future_event_thread():
    def llm(prompt):
        return {
            "thread_detected": True,
            "summary": "has a job interview coming up",
            "thread_type": "future_event",
            "importance_tier": "high",
            "emotional_weight": 0.7,
            "follow_up_in_hours": 30,
            "confidence": 0.85,
        }
    thread = te.extract_thread("I have an interview on Thursday, kind of nervous",
                               llm_fn=llm, now=NOW, source_session_id="s1")
    assert thread is not None
    assert thread.summary == "has a job interview coming up"
    assert thread.thread_type == ThreadType.FUTURE_EVENT
    assert thread.importance_tier == ImportanceTier.HIGH
    assert thread.status == ThreadStatus.UNRESOLVED
    assert thread.emotional_weight == 0.7
    assert thread.follow_up_due_at == NOW + timedelta(hours=30)
    assert thread.source_session_id == "s1"


def test_extract_below_confidence_threshold_returns_none():
    def llm(prompt):
        return {"thread_detected": True, "summary": "maybe something", "confidence": 0.3}
    assert te.extract_thread("i'll let you know tomorrow", llm_fn=llm, now=NOW) is None


def test_extract_no_thread_detected_returns_none():
    def llm(prompt):
        return {"thread_detected": False}
    assert te.extract_thread("remind me to check back", llm_fn=llm, now=NOW) is None


def test_extract_malformed_json_string_degrades_to_none():
    thread = te.extract_thread("I have an appointment tomorrow",
                               llm_fn=lambda p: "not json", now=NOW)
    assert thread is None


def test_extract_llm_exception_degrades_to_none():
    def broken(prompt):
        raise RuntimeError("llm unavailable")
    thread = te.extract_thread("I have an appointment tomorrow", llm_fn=broken, now=NOW)
    assert thread is None


def test_extract_invalid_enum_values_fall_back_to_safe_defaults():
    def llm(prompt):
        return {"thread_detected": True, "summary": "some pending thing",
                "thread_type": "not_a_real_type", "importance_tier": "not_a_real_tier",
                "confidence": 0.9}
    thread = te.extract_thread("waiting to hear back about something", llm_fn=llm, now=NOW)
    assert thread.thread_type == ThreadType.FACTUAL_PENDING
    assert thread.importance_tier == ImportanceTier.MEDIUM


def test_extract_accepts_a_json_string_payload():
    import json
    payload = json.dumps({"thread_detected": True, "summary": "will call mom back",
                          "thread_type": "intention_commitment", "confidence": 0.9})
    thread = te.extract_thread("i'll call my mom back tonight", llm_fn=lambda p: payload, now=NOW)
    assert thread is not None and thread.thread_type == ThreadType.INTENTION_COMMITMENT
