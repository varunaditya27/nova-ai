"""Tests for the Layer 10 engine — Layer10ContextPacket assembly (architecture doc §8)."""

from datetime import date

from backend.layer10_longitudinal import engine
from backend.layer10_longitudinal.schemas import (
    Layer10ContextPacket,
    LifeChapter,
    LifeDomainBalance,
    NarrativeArc,
    ProgressSnapshot,
    RetrospectivePacket,
    RetrospectiveType,
)

NOW = date(2025, 6, 1)


def _arc():
    ch = LifeChapter(title="Finding My Footing", start_date=date(2025, 1, 1), is_current=True,
                     primary_theme="career growth", narrative_summary="A steadier stretch.")
    arc = NarrativeArc(user_id="u1", arc_start_date=date(2024, 6, 1), chapters=[ch],
                       current_chapter=ch, running_growth_narrative="More grounded than a year ago.")
    return arc


def _retro(priority, surfaced=False):
    return RetrospectivePacket(user_id="u1", retrospective_type=RetrospectiveType.ONE_YEAR_AGO.value,
                               reference_date=date(2024, 6, 1), surfacing_priority=priority,
                               has_been_surfaced=surfaced)


def test_assemble_returns_context_packet():
    pkt = engine.assemble_context_packet("u1", narrative_arc=_arc(), days_since_started=365)
    assert isinstance(pkt, Layer10ContextPacket)
    assert pkt.current_chapter_summary == "A steadier stretch."
    assert pkt.current_chapter_theme == "career growth"
    assert pkt.days_since_nova_relationship_started == 365


def test_highest_priority_retrospective_selected():
    pkt = engine.assemble_context_packet(
        "u1", narrative_arc=_arc(), pending_retrospectives=[_retro(0.3), _retro(0.9), _retro(0.5)])
    assert pkt.highest_priority_retrospective.surfacing_priority == 0.9


def test_surfaced_retrospectives_excluded():
    pkt = engine.assemble_context_packet(
        "u1", narrative_arc=_arc(), pending_retrospectives=[_retro(0.9, surfaced=True), _retro(0.4)])
    assert pkt.highest_priority_retrospective.surfacing_priority == 0.4


def test_emotional_trend_reflects_snapshot():
    snap = ProgressSnapshot(user_id="u1", as_of_date=NOW, valence_trend_short="improving",
                            domain_balance=LifeDomainBalance(dominant_domain="career"))
    pkt = engine.assemble_context_packet("u1", narrative_arc=_arc(), progress_snapshot=snap)
    assert "improv" in pkt.emotional_trend_recent.lower()
    assert pkt.dominant_life_domain == "career"


def test_pending_sorted_by_priority_desc():
    pkt = engine.assemble_context_packet(
        "u1", narrative_arc=_arc(), pending_retrospectives=[_retro(0.2), _retro(0.8), _retro(0.5)])
    priorities = [r.surfacing_priority for r in pkt.pending_retrospectives]
    assert priorities == [0.8, 0.5, 0.2]


def test_empty_inputs_flag_insufficient_data():
    pkt = engine.assemble_context_packet("u1")
    assert isinstance(pkt, Layer10ContextPacket)
    assert pkt.minimum_data_threshold_met is False
