"""Enumerations for Layer 7 — Goals & Accountability Engine."""

from __future__ import annotations

from enum import Enum


# ── SC-1 signal strength ────────────────────────────────────────────────────
class GoalSignalStrength(str, Enum):
    EXPLICIT_STATED = "explicit_stated"
    IMPLICIT_ASPIRED = "implicit_aspired"
    REPEATED_THEME = "repeated_theme"
    ABANDONED_REVISIT = "abandoned_revisit"


# ── SC-2 goal enums ──────────────────────────────────────────────────────────
class GoalDomain(str, Enum):
    HEALTH = "health"
    CAREER = "career"
    RELATIONSHIPS = "relationships"
    LEARNING = "learning"
    FINANCE = "finance"
    CREATIVITY = "creativity"
    PERSONAL_GROWTH = "personal_growth"
    OTHER = "other"


class GoalDirection(str, Enum):
    ACHIEVE_OUTCOME = "achieve_outcome"
    BUILD_HABIT = "build_habit"
    STOP_BEHAVIOR = "stop_behavior"
    MAINTAIN_STATE = "maintain_state"
    DEVELOP_SKILL = "develop_skill"


class GoalStatus(str, Enum):
    TENTATIVE = "tentative"
    ACTIVE = "active"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    PAUSED = "paused"
    ABANDONED = "abandoned"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GoalSignalEventType(str, Enum):
    CREATED = "created"
    REAFFIRMED = "reaffirmed"
    PROGRESS_POSITIVE = "progress_positive"
    PROGRESS_NEGATIVE = "progress_negative"
    OBSTACLE_MENTIONED = "obstacle_mentioned"
    STRATEGY_MENTIONED = "strategy_mentioned"
    MOTIVATION_EXPRESSED = "motivation_expressed"
    DEADLINE_UPDATED = "deadline_updated"
    METRIC_UPDATED = "metric_updated"
    STATUS_CHANGED = "status_changed"
    MILESTONE_REACHED = "milestone_reached"
    MILESTONE_MISSED = "milestone_missed"
    HABIT_CHECKED = "habit_checked"
    ABANDONED = "abandoned"
    COMPLETED = "completed"
    PROACTIVE_SENT = "proactive_sent"
    PROACTIVE_RESPONDED = "proactive_responded"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    REACHED = "reached"
    MISSED = "missed"
    DEFERRED = "deferred"


class HabitFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    WEEKDAYS = "weekdays"
    CUSTOM = "custom"


# ── SC-3 / SC-4 enums ────────────────────────────────────────────────────────
class ProgressSignalType(str, Enum):
    PROGRESS_POSITIVE = "progress_positive"
    PROGRESS_NEGATIVE = "progress_negative"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalReferenceType(str, Enum):
    ACKNOWLEDGE_PROGRESS = "acknowledge_progress"
    ACKNOWLEDGE_SETBACK = "acknowledge_setback"
    CELEBRATE_COMPLETION = "celebrate_completion"
    CONNECT_TOPIC = "connect_topic"
    GENTLE_CHECK = "gentle_check"
    NONE = "none"


class GoalReferencePosition(str, Enum):
    OPENING = "opening"
    BODY = "body"
    CLOSING = "closing"
    NONE = "none"
