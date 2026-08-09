"""Schemas for Layer 10 — Longitudinal Life Layer (architecture doc §3-§8).

Pure-stdlib dataclasses + str-enums. Layer 10 stores *interpreted* representations (chapters,
patterns, metrics), never raw transcripts (§13.2). These types are the shared contract for the
Life Narrative Engine (SC-1), Weekly Summary Engine (SC-2), Progress & Pattern Tracker (SC-3),
Retrospective Engine (SC-4), and Life Calendar (SC-5).

The small input record types (EmotionalRecord, SessionRecord, EpisodicRecord) are Layer 10's
read-only view models of upstream data (Layers 1/2/3); goals are duck-typed (any object with
``status`` / ``created_at`` / ``status_changed_at`` works, e.g. Layer 7's Goal).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional


# ── Upstream view-model records (read-only inputs) ────────────────────────────
@dataclass
class EmotionalRecord:
    date: date
    valence: float = 0.0            # -1.0 .. 1.0
    arousal: float = 0.0            # 0.0 .. 1.0
    primary_emotion: str = "neutral"
    emotional_intensity: float = 0.0


@dataclass
class SessionRecord:
    session_id: str
    date: date
    duration_mins: float = 0.0
    user_message_length: float = 0.0
    self_disclosure_events: int = 0
    crisis_mode_active: bool = False


@dataclass
class EpisodicRecord:
    episode_id: str
    date: date
    importance_score: float = 0.0
    emotional_intensity: float = 0.0
    topics: list = field(default_factory=list)
    is_life_event_anchor: bool = False
    title: str = ""


# ── SC-1 Life Narrative (§3.2) ────────────────────────────────────────────────
class NarrativeRole(str, Enum):
    TURNING_POINT = "turning_point"
    ACHIEVEMENT = "achievement"
    SETBACK = "setback"
    DISCLOSURE = "disclosure"
    DECISION = "decision"
    REALIZATION = "realization"
    CONNECTION = "connection"


@dataclass
class EmotionalArcSummary:
    opening_valence: float = 0.0
    closing_valence: float = 0.0
    dominant_emotion: str = "neutral"
    emotional_range: float = 0.0
    trajectory: str = "mixed"        # improving|declining|stable_positive|stable_negative|
                                     # volatile|recovering|mixed
    notable_peaks: list = field(default_factory=list)    # (date, valence)
    notable_troughs: list = field(default_factory=list)


@dataclass
class NarrativeMoment:
    date: date
    title: str
    moment_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    episode_ids: list = field(default_factory=list)
    significance_score: float = 0.0
    narrative_role: str = NarrativeRole.REALIZATION.value
    reflection_prompt: Optional[str] = None


@dataclass
class LifeEvent:
    event_id: str
    user_id: str
    title: str
    category: str                    # career_transition|educational_transition|relational_major|
                                     # geographic_relocation|major_loss|health_major|other
    event_date: date
    significance_score: float = 0.5
    detected_at: Optional[datetime] = None
    associated_goal_id: Optional[str] = None
    description: Optional[str] = None


@dataclass
class LifeChapter:
    title: str
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    chapter_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    primary_theme: str = ""
    secondary_themes: list = field(default_factory=list)
    opening_context: str = ""
    defining_moments: list[NarrativeMoment] = field(default_factory=list)
    emotional_arc: Optional[EmotionalArcSummary] = None
    goals_active: list = field(default_factory=list)
    goals_resolved: list = field(default_factory=list)
    life_events: list = field(default_factory=list)
    growth_observed: list = field(default_factory=list)
    narrative_summary: str = ""
    synthesis_version: int = 0
    last_synthesized_at: Optional[datetime] = None


@dataclass
class NarrativeArc:
    user_id: str
    arc_start_date: date
    chapters: list[LifeChapter] = field(default_factory=list)
    current_chapter: Optional[LifeChapter] = None
    overall_themes: list = field(default_factory=list)
    running_growth_narrative: str = ""
    narrative_version: int = 0
    last_full_synthesis_at: Optional[datetime] = None


@dataclass
class ChapterSynthesis:
    narrative_summary: str = ""
    primary_theme: str = ""
    secondary_themes: list = field(default_factory=list)
    growth_observed: list = field(default_factory=list)
    revised_title: str = ""


# ── SC-2 Weekly Summary (§4.2) ────────────────────────────────────────────────
@dataclass
class WeeklyEmotionalSummary:
    avg_valence: float = 0.0
    avg_arousal: float = 0.0
    dominant_emotion: str = "neutral"
    emotional_range: float = 0.0
    high_intensity_sessions: int = 0
    trajectory: str = "stable"       # improving|declining|stable|volatile
    compared_to_previous_week: str = "not_enough_data"
    compared_to_baseline: str = "at_baseline"


@dataclass
class WeeklyProgressMetrics:
    session_frequency: float = 0.0
    avg_session_depth: float = 0.0
    goal_progress_velocity: float = 0.0
    new_goal_activation_count: int = 0
    goal_abandonment_count: int = 0
    avg_message_length_user: float = 0.0
    self_disclosure_events: int = 0
    crisis_events: int = 0


@dataclass
class WeeklySummary:
    user_id: str
    week_start_date: date
    week_end_date: date
    summary_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    generated_at: Optional[datetime] = None
    session_count: int = 0
    total_conversation_duration_mins: float = 0.0
    session_dates: list = field(default_factory=list)
    longest_gap_in_week_days: float = 0.0
    emotional_summary: Optional[WeeklyEmotionalSummary] = None
    most_emotionally_significant_moment: Optional[NarrativeMoment] = None
    primary_topics: list = field(default_factory=list)
    dominant_theme: str = ""
    new_topics_introduced: list = field(default_factory=list)
    goals_mentioned: list = field(default_factory=list)
    goals_progressed: list = field(default_factory=list)
    goals_stalled: list = field(default_factory=list)
    week_narrative: str = ""
    emotional_trajectory_this_week: str = "stable"
    standout_observation: Optional[str] = None
    progress_metrics: Optional[WeeklyProgressMetrics] = None
    minimum_data_threshold_met: bool = True


# ── SC-3 Progress & Pattern Tracker (§5.2) ────────────────────────────────────
class PatternType(str, Enum):
    EMOTIONAL_CYCLE = "emotional_cycle"
    BEHAVIORAL_AVOIDANCE = "behavioral_avoidance"
    POSITIVE_HABIT = "positive_habit"
    NEGATIVE_HABIT = "negative_habit"
    ENERGY_RHYTHM = "energy_rhythm"
    TOPIC_RECURRENCE = "topic_recurrence"


@dataclass
class BehavioralPattern:
    description: str
    pattern_type: str
    first_detected_date: date
    last_observed_date: date
    confidence: float = 0.0
    occurrence_count: int = 0
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    associated_goal_ids: list = field(default_factory=list)


@dataclass
class LifeDomainBalance:
    domain_weights: dict = field(default_factory=dict)
    dominant_domain: str = ""
    neglected_domains: list = field(default_factory=list)
    balance_score: float = 0.0
    balance_trend: str = "stable"    # concentrating|diversifying|stable


@dataclass
class ProgressSnapshot:
    """A compact longitudinal progress record (subset of the doc's full dimension set)."""
    user_id: str
    as_of_date: date
    snapshot_version: int = 0
    avg_valence_4w: float = 0.0
    avg_valence_12w: float = 0.0
    valence_trend_short: str = "stable"
    high_intensity_frequency: float = 0.0
    crisis_event_frequency: float = 0.0
    resilience_score: float = 0.0
    total_goals_lifetime: int = 0
    goals_achieved_lifetime: int = 0
    goals_abandoned_lifetime: int = 0
    achievement_rate_lifetime: float = 0.0
    avg_sessions_per_week_4w: float = 0.0
    domain_balance: Optional[LifeDomainBalance] = None
    active_patterns: list = field(default_factory=list)


# ── SC-4 Retrospective (§6.2) ─────────────────────────────────────────────────
class RetrospectiveType(str, Enum):
    ONE_WEEK_AGO = "one_week_ago"
    ONE_MONTH_AGO = "one_month_ago"
    THREE_MONTHS_AGO = "three_months_ago"
    SIX_MONTHS_AGO = "six_months_ago"
    ONE_YEAR_AGO = "one_year_ago"
    GOAL_ANNIVERSARY = "goal_anniversary"
    CHAPTER_CLOSE = "chapter_close"
    RELATIONSHIP_MILESTONE = "relationship_milestone"
    FIRST_YEAR_IN_REVIEW = "first_year_in_review"
    QUARTERLY_GROWTH = "quarterly_growth"
    PATTERN_SURFACING = "pattern_surfacing"


@dataclass
class ThenVsNow:
    then_primary_concern: str = ""
    now_primary_concern: str = ""
    then_emotional_state: str = ""
    now_emotional_state: str = ""
    then_active_goals: list = field(default_factory=list)
    now_active_goals: list = field(default_factory=list)
    key_change: str = ""


@dataclass
class RetrospectivePacket:
    user_id: str
    retrospective_type: str
    reference_date: date
    packet_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    generated_at: Optional[datetime] = None
    headline: str = ""
    narrative_reflection: str = ""
    then_vs_now: Optional[ThenVsNow] = None
    growth_highlights: list = field(default_factory=list)
    reflection_questions: list = field(default_factory=list)
    backing_episode_ids: list = field(default_factory=list)
    surfacing_priority: float = 0.0
    surfacing_window_days: int = 7
    has_been_surfaced: bool = False
    surfaced_at: Optional[datetime] = None
    user_engagement: Optional[str] = None


@dataclass
class YearInReview:
    user_id: str
    year: int
    chapter_count: int = 0
    total_sessions: int = 0
    goals_set: int = 0
    goals_achieved: int = 0
    goals_abandoned: int = 0
    goals_carrying_forward: int = 0
    emotional_arc: Optional[EmotionalArcSummary] = None
    defining_moments: list = field(default_factory=list)
    hardest_period_summary: Optional[str] = None
    best_period_summary: Optional[str] = None
    dominant_growth_theme: str = ""
    year_narrative: str = ""
    abbreviated: bool = False


# ── SC-5 Life Calendar (§7.2) ─────────────────────────────────────────────────
class CalendarEntryType(str, Enum):
    WEEKLY_SUMMARY_DUE = "weekly_summary_due"
    MONTHLY_NARRATIVE_UPDATE = "monthly_narrative_update"
    QUARTERLY_GROWTH_REVIEW = "quarterly_growth_review"
    ANNIVERSARY_1YEAR = "anniversary_1year"
    ANNIVERSARY_6MONTH = "anniversary_6month"
    ANNIVERSARY_3MONTH = "anniversary_3month"
    ANNIVERSARY_1MONTH = "anniversary_1month"
    GOAL_TARGET_DATE = "goal_target_date"
    GOAL_ANNIVERSARY = "goal_anniversary"
    GOAL_STALENESS_CHECK = "goal_staleness_check"
    LIFE_EVENT_ANNIVERSARY = "life_event_anniversary"
    CHAPTER_BOUNDARY_DETECTED = "chapter_boundary_detected"
    NOVA_RELATIONSHIP_DAY30 = "nova_relationship_day30"
    NOVA_RELATIONSHIP_DAY100 = "nova_relationship_day100"
    NOVA_RELATIONSHIP_DAY365 = "nova_relationship_day365"
    PENDING_THREAD_DUE = "pending_thread_due"
    PATTERN_DETECTED = "pattern_detected"


@dataclass
class Layer6Action:
    action_type: str = "background_update_only"   # surface_retrospective|generate_and_surface|
                                                  # queue_for_next_session|surface_if_session_opens
    urgency: str = "opportunistic"                # immediate|within_24h|within_week|opportunistic
    retrospective_packet_id: Optional[str] = None
    message_suggestion: Optional[str] = None


@dataclass
class CalendarEntry:
    user_id: str
    date: date
    entry_type: str
    title: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    associated_id: Optional[str] = None
    priority: float = 0.5
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    layer6_action: Optional[Layer6Action] = None
    lookback_days: int = 0
    has_fired: bool = False
    fired_at: Optional[datetime] = None


# ── Output contract (§8) ──────────────────────────────────────────────────────
@dataclass
class Layer10ContextPacket:
    user_id: str
    generated_at: Optional[datetime] = None
    current_chapter_summary: str = ""
    current_chapter_theme: str = ""
    running_growth_narrative: str = ""
    days_since_nova_relationship_started: int = 0
    emotional_trend_recent: str = ""
    primary_active_goals: list = field(default_factory=list)
    dominant_life_domain: str = ""
    pending_retrospectives: list = field(default_factory=list)
    highest_priority_retrospective: Optional[RetrospectivePacket] = None
    active_behavioral_patterns: list = field(default_factory=list)
    current_week_summary: Optional[WeeklySummary] = None
    last_week_summary: Optional[WeeklySummary] = None
    upcoming_goal_deadlines: list = field(default_factory=list)
    recent_life_event: Optional[LifeEvent] = None
    minimum_data_threshold_met: bool = True
