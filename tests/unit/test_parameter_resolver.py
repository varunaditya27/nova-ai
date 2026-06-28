"""Tests for SC: Parameter Resolver (architecture doc §6)."""

from datetime import datetime

from backend.layer8_tools import parameter_resolver as pr
from backend.layer8_tools.schemas import ActionType, Capability, ParameterGap, ToolIntent

NOW = datetime(2026, 6, 28, 9, 0)


def _cap(required):
    return Capability(operation="create_event", action_type=ActionType.CREATE.value,
                      required_params=required)


def _intent(params):
    return ToolIntent(tool_name="calendar", operation="create_event",
                      action_type=ActionType.CREATE.value, parameters=params)


# ── Gap detection (§6.2) ─────────────────────────────────────────────────────
def test_detects_missing_required_params():
    gaps = pr.detect_parameter_gaps(_intent({"title": "Dentist"}), _cap(["title", "start"]))
    assert [g.parameter_name for g in gaps] == ["start"]


def test_no_gaps_when_all_present():
    gaps = pr.detect_parameter_gaps(_intent({"title": "x", "start": "y"}), _cap(["title", "start"]))
    assert gaps == []


# ── One question per turn (§6.3) ─────────────────────────────────────────────
def test_clarification_question_mentions_param():
    q = pr.generate_clarification_question(ParameterGap("start", description="event start time"))
    assert q and "start" in q.lower()


def test_next_clarification_asks_only_one():
    q = pr.next_clarification(_intent({}), _cap(["title", "start"]))
    assert isinstance(q, str) and q  # a single string, not a list — never bombard


def test_next_clarification_none_when_complete():
    assert pr.next_clarification(_intent({"title": "x", "start": "y"}), _cap(["title"])) is None


# ── User-input normalization (§6.4) ──────────────────────────────────────────
def test_resolve_relative_date_tomorrow():
    val = pr.resolve_parameter(ParameterGap("start"), "tomorrow", now=NOW)
    assert val.startswith("2026-06-29")


def test_resolve_plain_value_is_trimmed():
    assert pr.resolve_parameter(ParameterGap("title"), "  Dentist  ", now=NOW) == "Dentist"


# ── Context inference (§6.5) ─────────────────────────────────────────────────
def test_infers_high_confidence_param_from_context():
    filled = pr.resolve_from_context(
        _intent({"title": "Dentist"}), _cap(["title", "start"]),
        infer_fn=lambda name, ctx: ("2026-07-01T09:00", 0.9), context="", threshold=0.85)
    assert filled.parameters["start"] == "2026-07-01T09:00"


def test_does_not_infer_low_confidence():
    filled = pr.resolve_from_context(
        _intent({"title": "Dentist"}), _cap(["title", "start"]),
        infer_fn=lambda name, ctx: ("guess", 0.4), context="", threshold=0.85)
    assert "start" not in filled.parameters
