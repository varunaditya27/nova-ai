"""Tests for SC-4 Retrospective Engine (architecture doc §6)."""

from datetime import date, timedelta
from types import SimpleNamespace

from backend.layer10_longitudinal import retrospective as retro
from backend.layer10_longitudinal.schemas import (
    NarrativeArc,
    ProgressSnapshot,
    RetrospectivePacket,
    RetrospectiveType,
    WeeklyEmotionalSummary,
    WeeklySummary,
    YearInReview,
)

TODAY = date(2025, 6, 1)


def _arc():
    return NarrativeArc(user_id="u1", arc_start_date=date(2024, 1, 1))


def _snapshot():
    return ProgressSnapshot(user_id="u1", as_of_date=TODAY, avg_valence_4w=0.3)


def _goal(title, status, created, changed=None):
    return SimpleNamespace(title=title, status=status, created_at=created,
                           status_changed_at=changed or created)


def _gen(rtype=RetrospectiveType.ONE_YEAR_AGO.value, ref=None, llm=None):
    return retro.generate_retrospective(
        retrospective_type=rtype, reference_date=ref or (TODAY - timedelta(days=365)),
        current_date=TODAY, narrative_arc=_arc(), weekly_summaries=[],
        progress_record=_snapshot(), goals=[], episodic_memories=[], llm_fn=llm)


# ── Surfacing windows (§6.3) ─────────────────────────────────────────────────
def test_surfacing_windows_table():
    assert retro.SURFACING_WINDOWS[RetrospectiveType.ONE_YEAR_AGO.value] == 30
    assert retro.SURFACING_WINDOWS[RetrospectiveType.ONE_WEEK_AGO.value] == 3


def test_packet_carries_window_from_table():
    p = _gen(rtype=RetrospectiveType.ONE_WEEK_AGO.value, ref=TODAY - timedelta(days=7))
    assert p.surfacing_window_days == 3


# ── Generation (§6.3) ────────────────────────────────────────────────────────
def test_generate_returns_packet():
    p = _gen()
    assert isinstance(p, RetrospectivePacket)
    assert p.retrospective_type == RetrospectiveType.ONE_YEAR_AGO.value
    assert p.headline and p.narrative_reflection


def test_llm_supplies_content():
    p = _gen(llm=lambda prompt: {"headline": "A year ago today...",
                                 "narrative": "You were just starting out.",
                                 "questions": ["What's changed most?"]})
    assert p.headline == "A year ago today..."
    assert p.reflection_questions == ["What's changed most?"]


def test_fallback_without_llm_is_grounded():
    p = _gen(llm=None)
    assert p.headline                            # non-empty factual headline


def test_backing_episodes_are_grounded():
    ep = SimpleNamespace(episode_id="e1", date=TODAY - timedelta(days=365),
                         importance_score=0.8, title="The first day")
    p = retro.generate_retrospective(
        retrospective_type=RetrospectiveType.ONE_YEAR_AGO.value,
        reference_date=TODAY - timedelta(days=365), current_date=TODAY, narrative_arc=_arc(),
        weekly_summaries=[], progress_record=_snapshot(), goals=[], episodic_memories=[ep])
    assert "e1" in p.backing_episode_ids


# ── Surfacing priority (§6.3) ────────────────────────────────────────────────
def test_priority_in_unit_interval():
    p = retro.compute_surfacing_priority(
        RetrospectiveType.ONE_YEAR_AGO.value, significance_of_reference_date=0.8, growth_magnitude=3)
    assert 0.0 <= p <= 1.0


def test_year_retrospective_higher_priority_than_week():
    year = retro.compute_surfacing_priority(RetrospectiveType.ONE_YEAR_AGO.value, 0.5, 1)
    week = retro.compute_surfacing_priority(RetrospectiveType.ONE_WEEK_AGO.value, 0.5, 1)
    assert year > week


# ── Year in Review (§6.4) ────────────────────────────────────────────────────
def test_year_in_review_aggregates_goals():
    goals = [
        _goal("Run a 10k", "achieved", date(2024, 2, 1), date(2024, 8, 1)),
        _goal("Learn piano", "abandoned", date(2024, 3, 1), date(2024, 6, 1)),
        _goal("Save money", "active", date(2024, 5, 1)),
    ]
    yir = retro.generate_year_in_review(
        user_id="u1", year_start=date(2024, 1, 1), year_end=date(2024, 12, 31),
        narrative_arc=_arc(), all_weekly_summaries=[], progress_record=_snapshot(), goals=goals)
    assert isinstance(yir, YearInReview)
    assert yir.goals_set == 3 and yir.goals_achieved == 1 and yir.goals_abandoned == 1


def test_year_in_review_picks_hardest_and_best_week():
    w_bad = WeeklySummary(user_id="u1", week_start_date=date(2024, 3, 4),
                          week_end_date=date(2024, 3, 10), week_narrative="A hard week.")
    w_bad.emotional_summary = WeeklyEmotionalSummary(avg_valence=-0.6)
    w_good = WeeklySummary(user_id="u1", week_start_date=date(2024, 7, 1),
                           week_end_date=date(2024, 7, 7), week_narrative="A great week.")
    w_good.emotional_summary = WeeklyEmotionalSummary(avg_valence=0.7)
    yir = retro.generate_year_in_review(
        user_id="u1", year_start=date(2024, 1, 1), year_end=date(2024, 12, 31),
        narrative_arc=_arc(), all_weekly_summaries=[w_bad, w_good],
        progress_record=_snapshot(), goals=[])
    assert yir.hardest_period_summary == "A hard week."
    assert yir.best_period_summary == "A great week."
