"""Layer 10 — Longitudinal Life Layer.

The temporal memory of a life lived alongside Nova: the only layer that looks backward across
months and years. A companion who holds your history is categorically different from one who
responds well in the present moment — growth is only visible with a before-state, and patterns
only emerge from repetition across long durations.

Five sub-components (all asynchronous; never on the message-response loop):

    SC-1  narrative_arc.py + life_narrative_engine.py  — Life Narrative Engine: chapter boundary
          detection, emotional-arc computation, and grounded chapter synthesis (injected LLM)
    SC-2  weekly_summary.py        — Weekly Summary Engine: synthesized 7-day digest
    SC-3  progress_tracker.py      — Progress & Pattern Tracker: rolling metrics, domain balance,
          behavioral pattern detection
    SC-4  retrospective.py         — Retrospective Engine: time-anchored look-backs + Year in Review
    SC-5  life_calendar.py         — Life Calendar: master scheduler / temporal index
    engine.assemble_context_packet — read-path Layer10ContextPacket for Layers 4 and 6 (§8)

Design commitments (architecture doc §13):
- Synthesis, not logging — Layer 10 stores interpreted structures, never raw transcripts.
- Never surface without grounding — every reflection cites specific episodic evidence; without
  an LLM, fallbacks emit only factual summaries, never invented interpretation (fabricated
  longitudinal memory is worse than none).
- Deterministic + offline-testable — all LLM synthesis is an injected ``llm_fn``, and all
  time-relative logic is keyed off an injected ``now`` / reference date.
- Depth of output matches depth of relationship (surfacing priority + data-sufficiency gating).

Reconciliation (as-built): the scaffold used scheduler-style names (NarrativeChapter, LifeDimension,
TurningPoint, RetrospectiveRecord); the implementation follows the authoritative doc's schema
(LifeChapter, NarrativeArc, ProgressSnapshot, RetrospectivePacket, etc.). A `life_calendar` module
(SC-5) and an `engine` (context-packet assembly) were added; `LifeEvent` detection lives in
`life_event_extractor.py` (no other layer owns it — see `docs/layer-10-architecture.md`'s Live
Wiring Status for the history of that finding).
"""

from backend.layer10_longitudinal import (
    engine,
    life_calendar,
    life_narrative_engine,
    narrative_arc,
    progress_tracker,
    retrospective,
    schemas,
    weekly_summary,
)
from backend.layer10_longitudinal.engine import assemble_context_packet
from backend.layer10_longitudinal.life_calendar import (
    LifeCalendar,
    map_entry_to_retrospective_type,
)
from backend.layer10_longitudinal.life_event_extractor import extract_life_event
from backend.layer10_longitudinal.life_narrative_engine import (
    extract_defining_moments,
    synthesize_chapter,
)
from backend.layer10_longitudinal.narrative_arc import (
    build_narrative_arc,
    compute_emotional_arc,
    detect_chapter_boundaries,
)
from backend.layer10_longitudinal.progress_tracker import (
    compute_domain_balance,
    compute_progress_snapshot,
    detect_behavioral_patterns,
)
from backend.layer10_longitudinal.retrospective import (
    SURFACING_WINDOWS,
    compute_surfacing_priority,
    generate_retrospective,
    generate_year_in_review,
)
from backend.layer10_longitudinal.weekly_summary import generate_weekly_summary
from backend.layer10_longitudinal.schemas import (
    BehavioralPattern,
    CalendarEntry,
    CalendarEntryType,
    ChapterSynthesis,
    EmotionalArcSummary,
    EmotionalRecord,
    EpisodicRecord,
    Layer6Action,
    Layer10ContextPacket,
    LifeChapter,
    LifeDomainBalance,
    LifeEvent,
    NarrativeArc,
    NarrativeMoment,
    PatternType,
    ProgressSnapshot,
    RetrospectivePacket,
    RetrospectiveType,
    SessionRecord,
    ThenVsNow,
    WeeklyEmotionalSummary,
    WeeklyProgressMetrics,
    WeeklySummary,
    YearInReview,
)

__all__ = [
    # modules
    "engine", "life_calendar", "life_narrative_engine", "narrative_arc", "progress_tracker",
    "retrospective", "schemas", "weekly_summary",
    # SC-1
    "build_narrative_arc", "compute_emotional_arc", "detect_chapter_boundaries",
    "extract_defining_moments", "synthesize_chapter",
    # SC-2
    "generate_weekly_summary",
    # SC-3
    "compute_domain_balance", "compute_progress_snapshot", "detect_behavioral_patterns",
    # SC-4
    "SURFACING_WINDOWS", "compute_surfacing_priority", "generate_retrospective",
    "generate_year_in_review",
    # SC-5 + engine
    "LifeCalendar", "map_entry_to_retrospective_type", "assemble_context_packet",
    "extract_life_event",
    # schemas
    "BehavioralPattern", "CalendarEntry", "CalendarEntryType", "ChapterSynthesis",
    "EmotionalArcSummary", "EmotionalRecord", "EpisodicRecord", "Layer6Action",
    "Layer10ContextPacket", "LifeChapter", "LifeDomainBalance", "LifeEvent", "NarrativeArc",
    "NarrativeMoment", "PatternType", "ProgressSnapshot", "RetrospectivePacket",
    "RetrospectiveType", "SessionRecord", "ThenVsNow", "WeeklyEmotionalSummary",
    "WeeklyProgressMetrics", "WeeklySummary", "YearInReview",
]
