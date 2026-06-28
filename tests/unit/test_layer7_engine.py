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


# ── §10 hard rule: never block on internal error ─────────────────────────────
def test_never_blocks_on_store_error():
    class BrokenStore(GoalStore):
        def get_relevant_goals(self, *a, **k):
            raise RuntimeError("store down")

    out = _run(BrokenStore([_goal()]), "I made progress")
    assert isinstance(out, Layer7Output)
    assert out.goal_context_packet.should_reference_goal is False
