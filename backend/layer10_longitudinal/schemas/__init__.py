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

from backend.layer10_longitudinal.schemas.calendar import (
    CalendarEntry,
    CalendarEntryType,
    Layer6Action,
)
from backend.layer10_longitudinal.schemas.context_packet import Layer10ContextPacket
from backend.layer10_longitudinal.schemas.narrative import (
    ChapterSynthesis,
    EmotionalArcSummary,
    LifeChapter,
    LifeEvent,
    NarrativeArc,
    NarrativeMoment,
    NarrativeRole,
)
from backend.layer10_longitudinal.schemas.progress import (
    BehavioralPattern,
    LifeDomainBalance,
    PatternType,
    ProgressSnapshot,
)
from backend.layer10_longitudinal.schemas.records import (
    EmotionalRecord,
    EpisodicRecord,
    SessionRecord,
)
from backend.layer10_longitudinal.schemas.retrospective import (
    RetrospectivePacket,
    RetrospectiveType,
    ThenVsNow,
    YearInReview,
)
from backend.layer10_longitudinal.schemas.weekly import (
    WeeklyEmotionalSummary,
    WeeklyProgressMetrics,
    WeeklySummary,
)

__all__ = [
    # upstream records
    "EmotionalRecord", "SessionRecord", "EpisodicRecord",
    # SC-1
    "NarrativeRole", "EmotionalArcSummary", "NarrativeMoment", "LifeEvent", "LifeChapter",
    "NarrativeArc", "ChapterSynthesis",
    # SC-2
    "WeeklyEmotionalSummary", "WeeklyProgressMetrics", "WeeklySummary",
    # SC-3
    "PatternType", "BehavioralPattern", "LifeDomainBalance", "ProgressSnapshot",
    # SC-4
    "RetrospectiveType", "ThenVsNow", "RetrospectivePacket", "YearInReview",
    # SC-5
    "CalendarEntryType", "Layer6Action", "CalendarEntry",
    # output contract
    "Layer10ContextPacket",
]
