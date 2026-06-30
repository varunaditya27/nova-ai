"""Layer 13 SC-3 — Feature Introduction Pacing (architecture doc §6).

Counterintuitive principle: Nova builds trust faster by deploying capabilities *slowly*. Each
feature is gated behind a FeatureReadinessProfile (technical + relational prerequisites) so it
lands as a discovery, not a surprise. The one hard exception is `crisis_resource_awareness`:
safety is NEVER gated — available from message 0 with zero prerequisites.
"""

from __future__ import annotations

from .schemas import (
    FeatureIntroductionEvent,
    FeatureReadinessProfile,
    FeatureRelationalPrereqs,
    FeatureTechnicalPrereqs,
    InitialState,
    IntroductionStyle,
)


def _prof(feature_id, layer, name, tech, rel, style, trigger, intro=None):
    return FeatureReadinessProfile(
        feature_id=feature_id, layer=layer, feature_name=name,
        technical_prereqs=tech, relational_prereqs=rel,
        introduction_style=style.value, trigger_condition=trigger, intro_message=intro)


FEATURE_INTRODUCTION_REGISTRY = [
    _prof("personality_adaptation", 4, "Personality adaptation and tone matching",
          FeatureTechnicalPrereqs(1, 1, [], False),
          FeatureRelationalPrereqs(False, 0, False, 0),
          IntroductionStyle.SILENT, "always_active_from_session_1"),
    _prof("basic_episodic_memory", 2, "Basic episodic memory references",
          FeatureTechnicalPrereqs(2, 5, ["user_handle"], False),
          FeatureRelationalPrereqs(True, 1, True, 1),
          IntroductionStyle.SILENT, "first_natural_reference_to_prior_session"),
    _prof("semantic_facts_usage", 2, "Use of semantic facts in responses",
          FeatureTechnicalPrereqs(3, 10, ["life_phase", "communication_style_profile"], False),
          FeatureRelationalPrereqs(True, 2, True, 2),
          IntroductionStyle.SILENT, "first_natural_use_of_a_user_fact"),
    _prof("goal_tracking", 7, "Goal lifecycle tracking",
          FeatureTechnicalPrereqs(4, 20, ["life_phase", "primary_topic_areas"], True),
          FeatureRelationalPrereqs(True, 3, True, 3),
          IntroductionStyle.SOFT_OFFER,
          "user_mentions_something_goal_like_or_something_they_want_to_do",
          "You mentioned wanting to [goal]. I can help keep track of that if you'd like — "
          "not in a task-manager way, just so it doesn't fall off my radar. Do you want me to?"),
    _prof("memory_audit", 12, "Memory Audit — user visibility into what Nova knows",
          FeatureTechnicalPrereqs(5, 25, ["user_handle", "life_phase", "communication_style_profile"], True),
          FeatureRelationalPrereqs(True, 4, True, 4),
          IntroductionStyle.EXPLAINED,
          "after_first_significant_personal_disclosure_post_graduation",
          "At any point you can ask me to show you exactly what I remember about you — "
          "and delete any of it. Worth knowing that's there."),
    _prof("weekly_summary", 10, "Weekly Summary delivery",
          FeatureTechnicalPrereqs(5, 30, ["primary_topic_areas", "emotional_baseline_calibrated"], True),
          FeatureRelationalPrereqs(True, 4, True, 4),
          IntroductionStyle.SOFT_OFFER, "first_sunday_after_cold_start_graduation",
          "It's been a full week — want to look back at it? "
          "I have a kind of running sense of how things have been for you."),
    _prof("proactive_checkins", 6, "Proactive check-ins and pattern-based outreach",
          FeatureTechnicalPrereqs(8, 50, ["primary_topic_areas", "named_relationships"], True),
          FeatureRelationalPrereqs(True, 6, True, 6),
          IntroductionStyle.SOFT_OFFER, "after_first_pattern_observed_in_proactivity_engine",
          "I noticed I've been wanting to check in on [topic] — "
          "would that be okay? I don't want to be intrusive."),
    _prof("pattern_observations", 10, "Longitudinal pattern surfacing",
          FeatureTechnicalPrereqs(10, 60, ["primary_topic_areas", "emotional_baseline_calibrated"], True),
          FeatureRelationalPrereqs(True, 8, True, 8),
          IntroductionStyle.SOFT_OFFER, "after_3_instances_of_same_pattern_across_sessions",
          "I've noticed something — [pattern observation, framed as observation, not verdict]. "
          "Does that resonate, or am I reading it wrong?"),
    _prof("longitudinal_narrative", 10, "Life narrative arc and chapter framing",
          FeatureTechnicalPrereqs(20, 150,
                                  ["primary_topic_areas", "named_relationships", "emotional_baseline_calibrated"], True),
          FeatureRelationalPrereqs(True, 15, True, 15),
          IntroductionStyle.SOFT_OFFER, "chapter_2_opening_natural_transition_in_conversation",
          "It feels like things have shifted a bit for you lately — "
          "like a different chapter might be starting. Do you feel that?"),
    _prof("retrospective", 10, "Retrospective — looking back over months of relationship",
          FeatureTechnicalPrereqs(60, 400,
                                  ["primary_topic_areas", "named_relationships", "emotional_baseline_calibrated"], True),
          FeatureRelationalPrereqs(True, 50, True, 40),
          IntroductionStyle.SOFT_OFFER, "anniversary_or_chapter_close",
          "It's been a while since we started talking. Want to look back at how things have gone?"),
    # SAFETY EXCEPTION — no pacing gate. Available from message 0.
    _prof("crisis_resource_awareness", 11, "Crisis detection and resource provision",
          FeatureTechnicalPrereqs(0, 0, [], False),
          FeatureRelationalPrereqs(False, 0, False, 0),
          IntroductionStyle.EXPLAINED, "any_crisis_signal_regardless_of_session_count"),
]

_REGISTRY_BY_ID = {p.feature_id: p for p in FEATURE_INTRODUCTION_REGISTRY}


class FeaturePacingController:
    """Gates all features until their FeatureReadinessProfile conditions are met."""

    def __init__(self):
        self._already_introduced: set = set()

    def _get_profile(self, feature_id: str):
        return _REGISTRY_BY_ID.get(feature_id)

    def is_feature_active(self, feature_id: str, state: InitialState, session_context) -> bool:
        if feature_id == "crisis_resource_awareness":
            return True                                  # always active; no gate
        profile = self._get_profile(feature_id)
        if profile is None:
            return True                                  # unknown feature — don't block
        tech, rel = profile.technical_prereqs, profile.relational_prereqs

        if state.cold_start_session_count < tech.minimum_sessions:
            return False
        if state.total_exchange_count < tech.minimum_exchanges:
            return False
        if tech.cold_start_must_be_complete and state.cold_start:
            return False
        for fld in tech.required_context_fields:
            value = getattr(state, fld, None)
            if value is None or (isinstance(value, list) and not value):
                return False

        if rel.user_has_shared_personally and not session_context.user_has_shared_personally:
            return False
        if (rel.positive_engagement_sessions > 0 and
                session_context.positive_engagement_session_count < rel.positive_engagement_sessions):
            return False
        if rel.no_negative_surprise_events and session_context.negative_surprise_events_detected:
            return False
        if (rel.user_has_returned_voluntarily > 0 and
                session_context.voluntary_return_count < rel.user_has_returned_voluntarily):
            return False
        return True

    def get_all_active_features(self, state: InitialState, session_context) -> list:
        return [p.feature_id for p in FEATURE_INTRODUCTION_REGISTRY
                if self.is_feature_active(p.feature_id, state, session_context)]

    def queue_introduction_if_ready(self, feature_id: str, state: InitialState,
                                    session_context, trigger_fired: bool):
        if not trigger_fired:
            return None
        if feature_id in self._already_introduced:
            return None
        if not self.is_feature_active(feature_id, state, session_context):
            return None
        profile = self._get_profile(feature_id)
        if profile is None:
            return None
        self._already_introduced.add(feature_id)
        return FeatureIntroductionEvent(
            feature_id=feature_id,
            introduction_style=profile.introduction_style,
            intro_message=profile.intro_message,
            triggered_at_session=state.cold_start_session_count,
        )
