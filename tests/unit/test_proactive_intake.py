"""Tests for Layer 6 intake contracts (architecture doc §9)."""

from datetime import datetime, timedelta
from uuid import uuid4

from backend.layer6_proactivity import intake
from backend.layer6_proactivity.schemas import ProactiveItemType
from backend.layer1_input.schemas import NarrativeThread
from backend.layer5_relationship.schemas import CoachingOpportunity, SocialEvent

NOW = datetime(2026, 6, 28, 12, 0, 0)


def _thread(event_offset_days, summary="User mentioned an interview coming up.", weight=0.6):
    return NarrativeThread(thread_id=uuid4(), summary=summary, created_at=NOW,
                           follow_up_due_at=NOW + timedelta(days=event_offset_days),
                           emotional_weight=weight)


# ── §9.1 Layer 1 threads ─────────────────────────────────────────────────────
def test_thread_in_past_is_follow_up():
    item = intake.on_thread_due(_thread(-2), now=NOW)
    assert item.item_type == ProactiveItemType.THREAD_FOLLOW_UP.value
    assert item.source_layer == "layer1"
    # earliest send is 18h after the event date
    assert item.earliest_send_time == (NOW - timedelta(days=2)) + timedelta(hours=18)


def test_thread_in_future_is_upcoming_reminder():
    item = intake.on_thread_due(_thread(3), now=NOW)
    assert item.item_type == ProactiveItemType.UPCOMING_DATE_REMINDER.value
    assert item.content_basis_valence == 0.6        # carried from emotional_weight


# ── §9.2 Layer 2 post-distress gap ───────────────────────────────────────────
def test_post_distress_creates_emotional_check_in():
    item = intake.on_post_distress_gap(
        session_summary="Tough week; user felt overwhelmed about finals.",
        episode_id="ep1", end_valence=-0.7, gap_days=4, now=NOW)
    assert item is not None
    assert item.item_type == ProactiveItemType.EMOTIONAL_CHECK_IN.value
    assert item.base_priority == 0.85


def test_post_distress_none_when_gap_too_short():
    assert intake.on_post_distress_gap("s", "ep1", end_valence=-0.7, gap_days=1, now=NOW) is None


def test_post_distress_none_when_not_distressed():
    assert intake.on_post_distress_gap("s", "ep1", end_valence=-0.2, gap_days=5, now=NOW) is None


# ── §9.3 Layer 5 deferred coaching ───────────────────────────────────────────
def test_deferred_coaching_has_two_day_delay():
    opp = CoachingOpportunity(opportunity_detected=False, coaching_type="pattern_reflection",
                              triggering_person="p1",
                              triggering_event=SocialEvent(event_id="e1"),
                              observation_text="You've described this conflict a few times.")
    item = intake.on_deferred_coaching(opp, person_display_name="Riya", now=NOW)
    assert item.item_type == ProactiveItemType.SOCIAL_PATTERN_COACHING.value
    assert item.person_id == "p1"
    assert item.person_display_name == "Riya"
    assert item.earliest_send_time == NOW + timedelta(days=2)
    assert "e1" in item.source_event_ids


# ── §9.4 Layer 7 goal milestone ──────────────────────────────────────────────
def test_goal_milestone_creates_goal_check_in():
    due = NOW + timedelta(days=2)
    item = intake.on_goal_milestone_approaching(
        goal_id="g1", goal_title="Run a 5k", milestone_description="First training run",
        due_date=due, now=NOW)
    assert item.item_type == ProactiveItemType.GOAL_CHECK_IN.value
    assert item.source_goal_id == "g1"
    assert item.earliest_send_time == due - timedelta(days=1)
    assert "Run a 5k" in item.content_basis
