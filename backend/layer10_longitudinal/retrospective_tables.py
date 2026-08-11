"""SC-4 static surfacing tables — window/priority/label lookups by RetrospectiveType (§6.3).

Split out of ``retrospective.py``.
"""

from __future__ import annotations

from backend.layer10_longitudinal.schemas import RetrospectiveType

# Surfacing windows in days (architecture doc §6.3).
SURFACING_WINDOWS = {
    RetrospectiveType.ONE_WEEK_AGO.value: 3,
    RetrospectiveType.ONE_MONTH_AGO.value: 7,
    RetrospectiveType.THREE_MONTHS_AGO.value: 14,
    RetrospectiveType.SIX_MONTHS_AGO.value: 21,
    RetrospectiveType.ONE_YEAR_AGO.value: 30,
    RetrospectiveType.GOAL_ANNIVERSARY.value: 14,
    RetrospectiveType.CHAPTER_CLOSE.value: 7,
    RetrospectiveType.RELATIONSHIP_MILESTONE.value: 3,
    RetrospectiveType.FIRST_YEAR_IN_REVIEW.value: 60,
    RetrospectiveType.QUARTERLY_GROWTH.value: 14,
    RetrospectiveType.PATTERN_SURFACING.value: 21,
}

# Base surfacing priority by type — depth of output matches depth of moment (§13.5).
_BASE_PRIORITY = {
    RetrospectiveType.ONE_WEEK_AGO.value: 0.30,
    RetrospectiveType.ONE_MONTH_AGO.value: 0.45,
    RetrospectiveType.THREE_MONTHS_AGO.value: 0.55,
    RetrospectiveType.SIX_MONTHS_AGO.value: 0.70,
    RetrospectiveType.ONE_YEAR_AGO.value: 0.85,
    RetrospectiveType.GOAL_ANNIVERSARY.value: 0.60,
    RetrospectiveType.CHAPTER_CLOSE.value: 0.60,
    RetrospectiveType.RELATIONSHIP_MILESTONE.value: 0.70,
    RetrospectiveType.FIRST_YEAR_IN_REVIEW.value: 0.95,
    RetrospectiveType.QUARTERLY_GROWTH.value: 0.55,
    RetrospectiveType.PATTERN_SURFACING.value: 0.60,
}

LABELS = {
    RetrospectiveType.ONE_WEEK_AGO.value: "A week ago",
    RetrospectiveType.ONE_MONTH_AGO.value: "A month ago",
    RetrospectiveType.THREE_MONTHS_AGO.value: "Three months ago",
    RetrospectiveType.SIX_MONTHS_AGO.value: "Six months ago",
    RetrospectiveType.ONE_YEAR_AGO.value: "A year ago",
}


def compute_surfacing_priority(
    retrospective_type: str, significance_of_reference_date: float, growth_magnitude: int,
) -> float:
    """Blend type base, reference-date significance, and growth into a [0,1] priority (§6.3)."""
    base = _BASE_PRIORITY.get(retrospective_type, 0.5)
    growth = min(growth_magnitude, 5) / 5
    priority = base * 0.6 + significance_of_reference_date * 0.25 + growth * 0.15
    return round(max(0.0, min(1.0, priority)), 4)
