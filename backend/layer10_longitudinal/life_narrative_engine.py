"""SC-1 — Life Narrative Engine: chapter synthesis (architecture doc §3.3).

Synthesizes a chapter's human-readable narrative from grounded evidence. Synthesis is *not*
free-form generation: it extracts defining moments by significance, builds a citation-constrained
prompt, and calls an injected ``llm_fn``. Without a model (or on failure) it falls back to a
**grounded factual** summary built only from the evidence — never invented interpretation
(§13.3: fabricated longitudinal memory is worse than none).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, Optional

from backend.layer10_longitudinal.narrative_arc import compute_emotional_arc
from backend.layer10_longitudinal.schemas import (
    ChapterSynthesis,
    LifeChapter,
    NarrativeMoment,
)

_SIGNIFICANCE_IMPORTANCE = 0.70
_SIGNIFICANCE_INTENSITY = 0.75

NARRATIVE_SYNTHESIS_PROMPT_TEMPLATE = """\
You are synthesizing a chapter of someone's life as witnessed by their AI companion Nova.

Write a chapter summary that is grounded EXCLUSIVELY in the evidence below (do not invent
details), third person, past tense, 3-5 sentences, compassionate but honest.

EVIDENCE:
Significant moments: {significant_moments}
Emotional arc: {emotional_arc}
Life events: {life_events}
Goals active/resolved: {chapter_goals}

EXISTING CHAPTER TITLE: {existing_title}

Output ONLY JSON with keys: narrative_summary, primary_theme, secondary_themes (list),
growth_observed (list), revised_title.
"""


def extract_defining_moments(episodic_records: list, threshold: float = _SIGNIFICANCE_IMPORTANCE):
    """Select narrative-worthy episodes by significance (architecture doc §3.3 step 1)."""
    moments = []
    for e in episodic_records:
        if (e.importance_score >= threshold or e.emotional_intensity >= _SIGNIFICANCE_INTENSITY
                or e.is_life_event_anchor):
            moments.append(NarrativeMoment(
                date=e.date, title=e.title or "A moment", episode_ids=[e.episode_id],
                significance_score=max(e.importance_score, e.emotional_intensity)))
    return moments


def build_narrative_synthesis_prompt(
    significant_moments, emotional_arc, life_events, chapter_goals, existing_title,
) -> str:
    """Assemble the grounded, citation-constrained synthesis prompt (architecture doc §3.3)."""
    moment_lines = "; ".join(getattr(m, "title", str(m)) for m in significant_moments) or "none"
    event_lines = "; ".join(getattr(e, "title", str(e)) for e in life_events) or "none"
    return NARRATIVE_SYNTHESIS_PROMPT_TEMPLATE.format(
        significant_moments=moment_lines, emotional_arc=emotional_arc,
        life_events=event_lines, chapter_goals=chapter_goals or "none",
        existing_title=existing_title)


def _grounded_fallback(chapter: LifeChapter, moments, life_events) -> ChapterSynthesis:
    """A factual, evidence-only summary used when no LLM is available (§13.3)."""
    span = f"{chapter.start_date.isoformat()} to " + (
        chapter.end_date.isoformat() if chapter.end_date else "present")
    summary = (f"This chapter ({span}) includes {len(moments)} significant moment(s)"
               f" and {len(life_events)} life event(s).")
    return ChapterSynthesis(narrative_summary=summary, primary_theme=chapter.primary_theme,
                            secondary_themes=[], growth_observed=[], revised_title="")


def _coerce(raw) -> Optional[dict]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None
    return None


def synthesize_chapter(
    chapter: LifeChapter,
    episodic_records: list,
    life_events: list,
    goals: list,
    emotional_records: list,
    llm_fn: Optional[Callable[[str], object]] = None,
    now: Optional[datetime] = None,
) -> ChapterSynthesis:
    """Synthesize and apply a chapter narrative; always returns a grounded result (doc §3.3)."""
    now = now or datetime.utcnow()
    moments = extract_defining_moments(episodic_records)
    chapter.defining_moments = moments
    chapter.emotional_arc = compute_emotional_arc(emotional_records)

    synthesis: Optional[ChapterSynthesis] = None
    if llm_fn is not None:
        prompt = build_narrative_synthesis_prompt(
            moments, chapter.emotional_arc.trajectory, life_events, {}, chapter.title)
        try:
            data = _coerce(llm_fn(prompt))
        except Exception:
            data = None
        if data is not None:
            synthesis = ChapterSynthesis(
                narrative_summary=data.get("narrative_summary", ""),
                primary_theme=data.get("primary_theme", ""),
                secondary_themes=data.get("secondary_themes", []) or [],
                growth_observed=data.get("growth_observed", []) or [],
                revised_title=data.get("revised_title", "") or "")

    if synthesis is None:
        synthesis = _grounded_fallback(chapter, moments, life_events)

    # Apply to the chapter.
    if synthesis.narrative_summary:
        chapter.narrative_summary = synthesis.narrative_summary
    if synthesis.primary_theme:
        chapter.primary_theme = synthesis.primary_theme
    if synthesis.secondary_themes:
        chapter.secondary_themes = synthesis.secondary_themes
    if synthesis.growth_observed:
        chapter.growth_observed = synthesis.growth_observed
    if synthesis.revised_title:
        chapter.title = synthesis.revised_title
    chapter.synthesis_version += 1
    chapter.last_synthesized_at = now
    return synthesis
