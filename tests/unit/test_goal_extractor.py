"""Tests for SC-1 Goal Extractor (architecture doc §3)."""

from backend.layer7_goals import goal_extractor as ge
from backend.layer7_goals.schemas import Goal


def _active(title, goal_id="g1"):
    return Goal(goal_id=goal_id, title=title)


# ── Pre-filter (§3.3) ────────────────────────────────────────────────────────
def test_should_run_extractor_on_goal_keyword():
    assert ge.should_run_extractor("I really want to get fit before summer") is True
    assert ge.should_run_extractor("been meaning to learn guitar") is True


def test_should_not_run_extractor_on_neutral_message():
    assert ge.should_run_extractor("the weather is nice today") is False


# ── Deduplication (§3.5) ─────────────────────────────────────────────────────
def test_is_duplicate_goal_true_on_high_similarity():
    dup, gid = ge.is_duplicate_goal("get fit and exercise more",
                                    [_active("get fit before summer")],
                                    similarity_fn=lambda a, b: 0.9)
    assert dup is True and gid == "g1"


def test_is_duplicate_goal_false_on_low_similarity():
    dup, gid = ge.is_duplicate_goal("learn the guitar",
                                    [_active("save more money")],
                                    similarity_fn=lambda a, b: 0.1)
    assert dup is False and gid is None


# ── Extraction (§3.4) — LLM injected ─────────────────────────────────────────
def test_extract_no_keyword_returns_not_detected():
    res = ge.extract_goal("the sky is blue", llm_fn=lambda p: {"goal_detected": True})
    assert res.goal_detected is False


def test_extract_no_llm_returns_not_detected():
    # Extraction is LLM-driven; the pre-filter alone does not create goals.
    res = ge.extract_goal("I want to run a marathon")
    assert res.goal_detected is False


def test_extract_new_goal_via_llm():
    def llm(prompt):
        return {
            "goal_detected": True, "is_update": False,
            "new_goal": {"raw_statement": "I want to run a marathon",
                         "inferred_title": "Run a marathon",
                         "inferred_domain": "health", "inferred_direction": "achieve_outcome",
                         "confidence": 0.9, "signal_strength": "explicit_stated"},
        }

    res = ge.extract_goal("I want to run a marathon", llm_fn=llm)
    assert res.goal_detected is True
    assert res.is_update is False
    assert res.new_goal_data["inferred_title"] == "Run a marathon"
    assert res.confidence == 0.9


def test_extract_update_to_existing_goal():
    def llm(prompt):
        return {"goal_detected": True, "is_update": True, "goal_id_if_update": "g1",
                "update_type": "progress_positive", "update_description": "went running 3x"}

    res = ge.extract_goal("I went running three times this week, made progress",
                          active_goals=[_active("Run a marathon")], llm_fn=llm)
    assert res.is_update is True
    assert res.goal_id_if_update == "g1"
    assert res.update_type == "progress_positive"


def test_extract_new_goal_deduplicated_against_existing():
    def llm(prompt):
        return {"goal_detected": True, "is_update": False,
                "new_goal": {"inferred_title": "get fit", "confidence": 0.8}}

    res = ge.extract_goal("I want to get fit", active_goals=[_active("get in shape")],
                          llm_fn=llm, similarity_fn=lambda a, b: 0.95)
    assert res.was_duplicate is True
    assert res.matched_goal_id == "g1"


def test_extract_llm_reports_no_goal():
    res = ge.extract_goal("I want to vent about my day",
                          llm_fn=lambda p: {"goal_detected": False})
    assert res.goal_detected is False
