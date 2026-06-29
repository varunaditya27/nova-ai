"""Tests for SC-1 Life Narrative Engine — chapter synthesis (architecture doc §3.3)."""

from datetime import date, timedelta

from backend.layer10_longitudinal import life_narrative_engine as lne
from backend.layer10_longitudinal.schemas import (
    ChapterSynthesis,
    EpisodicRecord,
    LifeChapter,
)

START = date(2025, 1, 1)


def _chapter():
    return LifeChapter(title="The Internship Search", start_date=START,
                       end_date=START + timedelta(days=90), is_current=False)


def _ep(days, importance=0.5, intensity=0.5, anchor=False, title="chat", topics=None):
    return EpisodicRecord(episode_id=f"ep{days}", date=START + timedelta(days=days),
                          importance_score=importance, emotional_intensity=intensity,
                          is_life_event_anchor=anchor, title=title, topics=topics or [])


# ── Defining moment extraction (§3.3 step 1) ─────────────────────────────────
def test_extract_defining_moments_by_significance():
    eps = [_ep(1, importance=0.9), _ep(2, importance=0.2), _ep(3, intensity=0.8),
           _ep(4, anchor=True), _ep(5, importance=0.3, intensity=0.3)]
    moments = lne.extract_defining_moments(eps)
    assert len(moments) == 3       # the 0.9 / 0.8-intensity / anchor episodes


# ── LLM-driven synthesis (§3.3) ──────────────────────────────────────────────
def test_synthesize_with_llm_applies_result():
    ch = _chapter()
    def fake_llm(prompt):
        return {"narrative_summary": "A focused, anxious stretch spent job-hunting.",
                "primary_theme": "career uncertainty", "secondary_themes": ["resilience"],
                "growth_observed": ["learned to handle rejection"],
                "revised_title": "The Search"}
    result = lne.synthesize_chapter(ch, episodic_records=[_ep(1, importance=0.9)],
                                    life_events=[], goals=[], emotional_records=[], llm_fn=fake_llm)
    assert isinstance(result, ChapterSynthesis)
    assert ch.narrative_summary == "A focused, anxious stretch spent job-hunting."
    assert ch.primary_theme == "career uncertainty"
    assert ch.title == "The Search"
    assert ch.synthesis_version == 1


def test_synthesize_parses_json_string():
    ch = _chapter()
    fake = lambda p: '{"narrative_summary": "x", "primary_theme": "t", "revised_title": "T"}'
    lne.synthesize_chapter(ch, [_ep(1, importance=0.9)], [], [], [], llm_fn=fake)
    assert ch.narrative_summary == "x" and ch.title == "T"


# ── Grounded fallback (§13.3 — never fabricate) ──────────────────────────────
def test_synthesize_without_llm_uses_grounded_fallback():
    ch = _chapter()
    result = lne.synthesize_chapter(ch, episodic_records=[_ep(1, importance=0.9)],
                                    life_events=[], goals=[], emotional_records=[], llm_fn=None)
    assert result.narrative_summary           # non-empty, factual
    assert ch.synthesis_version == 1
    assert ch.title == "The Internship Search"   # title unchanged without a model


def test_synthesize_llm_failure_falls_back():
    ch = _chapter()
    def boom(prompt):
        raise RuntimeError("llm down")
    result = lne.synthesize_chapter(ch, [_ep(1, importance=0.9)], [], [], [], llm_fn=boom)
    assert result.narrative_summary           # fell back, didn't raise


def test_build_prompt_includes_evidence():
    prompt = lne.build_narrative_synthesis_prompt(
        significant_moments=[_ep(1, importance=0.9, title="The Job Rejection")],
        emotional_arc="declining then recovering", life_events=[], chapter_goals={},
        existing_title="The Search")
    assert "The Job Rejection" in prompt and "The Search" in prompt
