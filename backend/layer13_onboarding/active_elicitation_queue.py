"""Layer 13 SC-1 — Active Elicitation Queue + Surfacing Policy (architecture doc §4.3-§4.4).

Active elicitation = questions Nova deliberately chooses to ask, embedded naturally in
conversation, NEVER front-loaded or asked in sequence. An item surfaces only when all three
surfacing conditions hold simultaneously (earn-before-asking, enforced in code):
  1. its natural trigger is active in the conversation,
  2. the emotional register is appropriate for its priority, and
  3. the per-session rate limit (max 1 in the first two weeks) is not exceeded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .schemas import ELICITATION_CATEGORIES, ElicitationItem

# Initial population of the elicitation queue (§4.3). Priority-sorted, NEVER asked in sequence.
INITIAL_ELICITATION_ITEMS = [
    ElicitationItem(
        category="identity", inference_target="user_handle", priority=1,
        question="Hey — what should I call you?",
        can_infer_without_asking=False,
        natural_triggers=["any_first_personal_address_moment", "user_says_hi_or_hello",
                          "end_of_first_exchange"],
    ),
    ElicitationItem(
        category="life_context", inference_target="life_phase", priority=1,
        question="Are you a student, or are you working? Or something else entirely?",
        can_infer_without_asking=True,
        natural_triggers=["user_mentions_exams_or_studying", "user_mentions_work_or_job",
                          "user_mentions_a_schedule", "user_asks_about_productivity",
                          "user_mentions_stress"],
    ),
    ElicitationItem(
        category="communication_pref", inference_target="verbosity_preference", priority=2,
        question=None, can_infer_without_asking=True, natural_triggers=[],
    ),
    ElicitationItem(
        category="reason_for_use", inference_target="primary_reason", priority=2,
        question="What made you want to try this?", can_infer_without_asking=False,
        natural_triggers=["session_2_or_3_any_reflective_moment",
                          "user_says_something_about_wanting_to_change",
                          "user_mentions_loneliness_or_isolation",
                          "user_mentions_needing_someone_to_talk_to"],
    ),
    ElicitationItem(
        category="relationships", inference_target="close_relationships", priority=2,
        question=None, can_infer_without_asking=True, natural_triggers=[],
    ),
    ElicitationItem(
        category="goals", inference_target="primary_goal_area", priority=3,
        question="Is there something you've been working toward lately?",
        can_infer_without_asking=True,
        natural_triggers=["user_mentions_wanting_to_do_something", "user_mentions_a_plan",
                          "user_asks_for_advice_about_direction"],
    ),
    ElicitationItem(
        category="emotional_style", inference_target="emotional_expression_style", priority=3,
        question=None, can_infer_without_asking=True, natural_triggers=[],
    ),
    ElicitationItem(
        category="values", inference_target="core_values_sketch", priority=3,
        question=None, can_infer_without_asking=True, natural_triggers=[],
    ),
]


@dataclass
class ElicitationQueue:
    user_id: str
    items: list = field(default_factory=list)       # priority-sorted; NEVER asked in sequence

    def _is_answered_or_inferred(self, item_id: str) -> bool:
        for it in self.items:
            if it.item_id == item_id:
                return it.status in ("answered", "inferred")
        return False

    def next_surfaceable_item(self, session_context, current_session_number: int,
                              emotional_intensity: float,
                              topic_in_progress: Optional[str]) -> Optional[ElicitationItem]:
        """Highest-priority waiting item whose trigger fired, prereqs met, register appropriate."""
        topic = topic_in_progress or ""
        for item in sorted(self.items, key=lambda i: i.priority):
            if item.status != "waiting":
                continue
            if not all(self._is_answered_or_inferred(p) for p in item.prerequisite_item_ids):
                continue
            if not any(trigger in topic for trigger in item.natural_triggers):
                continue
            if emotional_intensity > 0.60 and item.priority == 3:
                continue   # never surface nice-to-have during emotionally heavy sessions
            return item
        return None


class ElicitationSurfacingPolicy:
    """All three conditions must be true simultaneously for an item to surface (§4.4)."""

    EARLY_PERIOD_SESSIONS = 14
    MAX_ELICITATION_PER_SESSION = 1

    def can_surface(self, item: ElicitationItem, session_context, current_session_number: int,
                    emotional_intensity: float, elicitation_count_this_session: int) -> bool:
        # CONDITION 1: the topic has naturally arisen in conversation
        trigger_active = (item.status == "waiting" and bool(
            set(session_context.active_triggers).intersection(set(item.natural_triggers))))
        if not trigger_active:
            return False

        # CONDITION 2: emotional register appropriate for this item's priority
        if emotional_intensity > 0.60 and item.priority >= 3:
            return False
        if emotional_intensity > 0.80 and item.priority >= 2:
            return False

        # CONDITION 3: rate limit — max one active elicitation per session in the early period
        if (current_session_number <= self.EARLY_PERIOD_SESSIONS and
                elicitation_count_this_session >= self.MAX_ELICITATION_PER_SESSION):
            return False

        return True
