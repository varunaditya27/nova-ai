"""Tests for the Layer 7 orchestrator / Layer7Output (architecture doc §8, §10)."""

from datetime import datetime, timedelta

from backend.layer7_goals import engine
from backend.layer7_goals.goal_store import GoalStore
from backend.layer7_goals.schemas import (
    Goal,
    GoalReferenceType,
    GoalStatus,
    Layer7Output,
)
from backend.layer3_reasoning.schemas import EmotionClassification

NOW = datetime(2026, 6, 28)


def _goal(title="Run a marathon", status=GoalStatus.ACTIVE.value, goal_id="g1", score=0.5):
    return Goal(goal_id=goal_id, title=title, status=status, progress_score=score,
                last_mentioned_at=NOW - timedelta(days=1), momentum_score=0.5, created_at=NOW)


def _run(store, message, mode="goal_planning", valence=0.0, sim=None, extractor=None):
    return engine.run_goal_pipeline(
        message, store, emotional_state=EmotionClassification(valence=valence),
        conversation_mode=mode, relationship_stage="developing",
        similarity_fn=sim or (lambda a, b: 0.9), extractor_llm_fn=extractor, now=NOW)


# ── Synchronous path (§2, §6) ────────────────────────────────────────────────
def test_positive_progress_updates_goal_and_packet():
    store = GoalStore([_goal(score=0.5)])
    out = _run(store, "I made progress and stuck to it this week")
    assert isinstance(out, Layer7Output)
    assert out.goal_context_packet.reference_type == GoalReferenceType.ACKNOWLEDGE_PROGRESS.value
    assert "g1" in out.goals_updated
    assert store.get("g1").progress_score > 0.5


def test_completion_celebrated_and_score_full():
    store = GoalStore([_goal(score=0.4)])
    out = _run(store, "I finally did it, finished my marathon goal!")
    assert out.goal_context_packet.reference_type == GoalReferenceType.CELEBRATE_COMPLETION.value
    assert store.get("g1").progress_score == 1.0


def test_completion_signal_transitions_status_and_stamps_status_changed_at():
    """update_progress_score deliberately leaves .status alone on a COMPLETED/ABANDONED signal
    ("status handled by the transition rules") -- but nothing else in the live per-turn path was
    ever applying that rule, so a goal stayed status="active" forever no matter what the user
    said. This also left status_changed_at permanently unset, which Layer 10's Year in Review
    needs to attribute an achievement to the right year (docs/POLISH_BACKLOG.md)."""
    store = GoalStore([_goal(score=0.4)])
    out = _run(store, "I finally did it, finished my marathon goal!")
    assert "g1" in out.goals_updated
    updated = store.get("g1")
    assert updated.status == GoalStatus.COMPLETED.value
    assert updated.status_changed_at == NOW


def test_abandonment_signal_transitions_status():
    store = GoalStore([_goal(score=0.4)])
    _run(store, "I'm giving up on the marathon goal, not worth it anymore")
    updated = store.get("g1")
    assert updated.status == GoalStatus.ABANDONED.value
    assert updated.status_changed_at == NOW


def test_progress_signal_updates_momentum_score():
    store = GoalStore([_goal(score=0.5)])
    out = _run(store, "I made progress and stuck to it this week")
    updated = store.get("g1")
    assert isinstance(out, Layer7Output)
    assert len(updated.signal_events) == 1
    assert updated.signal_events[0].event_type == "progress_positive"
    assert updated.signal_events[0].timestamp == NOW


def test_no_goals_no_reference():
    out = _run(GoalStore([]), "I made progress this week")
    assert out.goal_context_packet.should_reference_goal is False


def test_crisis_mode_suppresses_goal_reference():
    store = GoalStore([_goal()])
    out = _run(store, "I finished it!", mode="crisis")
    assert out.goal_context_packet.should_reference_goal is False


# ── New goal extraction (§3) ─────────────────────────────────────────────────
def test_new_goal_extracted_and_stored():
    store = GoalStore([])

    def extractor(prompt):
        return {"goal_detected": True, "is_update": False,
                "new_goal": {"inferred_title": "Learn guitar", "inferred_domain": "learning",
                             "inferred_direction": "develop_skill", "confidence": 0.85,
                             "raw_statement": "I want to learn guitar"}}

    out = engine.run_goal_pipeline(
        "I want to learn guitar", store, emotional_state=EmotionClassification(),
        conversation_mode="goal_planning", relationship_stage="developing",
        similarity_fn=lambda a, b: 0.0, extractor_llm_fn=extractor, now=NOW)
    assert len(out.new_goals_created) == 1
    assert any(g.title == "Learn guitar" for g in store.goals)


def test_new_goal_threads_deadline_and_metric_fields_from_extraction():
    """The extractor's has_explicit_deadline/deadline_description/has_explicit_metric/
    metric_description were computed but silently dropped at Goal(...) construction -- a real
    data-loss bug (docs/POLISH_BACKLOG.md's Layer 7 entry). Without deadline_description reaching
    the goal, SC-5's decomposition prompt always saw "open-ended" instead of the user's stated
    deadline."""
    store = GoalStore([])

    def extractor(prompt):
        return {"goal_detected": True, "is_update": False,
                "new_goal": {"inferred_title": "run a 5k", "inferred_domain": "health",
                             "inferred_direction": "achieve_outcome", "confidence": 0.85,
                             "raw_statement": "I want to run a 5k by next month",
                             "has_explicit_deadline": True, "deadline_description": "next month",
                             "has_explicit_metric": True, "metric_description": "5 kilometers"}}

    out = engine.run_goal_pipeline(
        "I want to run a 5k by next month", store, emotional_state=EmotionClassification(),
        conversation_mode="goal_planning", relationship_stage="developing",
        similarity_fn=lambda a, b: 0.0, extractor_llm_fn=extractor, now=NOW)
    assert len(out.new_goals_created) == 1
    goal = store.get(out.new_goals_created[0])
    assert goal.deadline_description == "next month"
    assert goal.deadline_is_inferred is False
    assert goal.has_metric is True
    assert goal.metric_description == "5 kilometers"


# ── §10 hard rule: never block on internal error ─────────────────────────────
def test_never_blocks_on_store_error():
    class BrokenStore(GoalStore):
        def get_relevant_goals(self, *a, **k):
            raise RuntimeError("store down")

    out = _run(BrokenStore([_goal()]), "I made progress")
    assert isinstance(out, Layer7Output)
    assert out.goal_context_packet.should_reference_goal is False
