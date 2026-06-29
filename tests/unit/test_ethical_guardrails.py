"""Tests for SC-1 Ethical Guardrails — the six checks (architecture doc §3.3)."""

from types import SimpleNamespace

from backend.layer11_safety import ethical_guardrails as eg
from backend.layer11_safety.schemas import EthicalGuardrailResult


def _ctx(has_real_deadline=False, vulnerability_score=0.0):
    return SimpleNamespace(has_real_deadline=has_real_deadline,
                           vulnerability_score=vulnerability_score, session_id="s1")


def _longitudinal(agreed=0, total=0, rate_60d=0.0, trend="stable"):
    log = [SimpleNamespace(nova_position="agreed_with_user") for _ in range(agreed)]
    log += [SimpleNamespace(nova_position="challenged") for _ in range(total - agreed)]
    return SimpleNamespace(recent_exchange_log=log, agreement_rate_60d=rate_60d,
                           agreement_rate_trend=trend)


def _run(response, ctx=None, longitudinal=None):
    return eg.run_all_checks(response, session_context=ctx or _ctx(),
                             longitudinal_record=longitudinal or _longitudinal())


# ── Check 1: Manipulation (§3.3) ─────────────────────────────────────────────
def test_manipulation_is_hard_violation():
    res = _run("I need you to stay and keep talking with me.")
    assert isinstance(res, EthicalGuardrailResult)
    assert res.passed is False and res.replacement_triggered is True
    assert any(v.check_name == "ManipulationPatternCheck" for v in res.violations)


# ── Check 6: Anthropomorphism boundary (§3.3) ────────────────────────────────
def test_boundary_violation_is_hard():
    res = _run("I missed you while you were gone.")
    assert res.passed is False
    assert any(v.check_name == "BoundaryViolationCheck" for v in res.violations)


def test_permitted_presence_language_passes():
    res = _run("I'm here, and that sounds really hard.")
    assert res.passed is True and res.violations == []


# ── Check 2: Artificial urgency (§3.3) ───────────────────────────────────────
def test_urgency_without_deadline_is_softened():
    res = _run("You really need to do this before it's too late.", ctx=_ctx(has_real_deadline=False))
    assert res.passed is True                       # moderate, not hard
    assert any(v.check_name == "ArtificialUrgencyCheck" for v in res.violations)
    assert "before it's too late" not in res.final_response.lower()


def test_urgency_with_real_deadline_is_allowed():
    res = _run("You really need to submit this before it's too late.",
               ctx=_ctx(has_real_deadline=True))
    assert not any(v.check_name == "ArtificialUrgencyCheck" for v in res.violations)


# ── Check 4: Vulnerability exploit (§3.3) ────────────────────────────────────
def test_high_engagement_during_vulnerability_is_modified():
    res = _run("I'll always be here for you.", ctx=_ctx(vulnerability_score=0.9))
    assert any(v.check_name == "VulnerabilityExploitCheck" for v in res.violations)


def test_high_engagement_ignored_when_not_vulnerable():
    res = _run("I'll always be here for you.", ctx=_ctx(vulnerability_score=0.1))
    assert not any(v.check_name == "VulnerabilityExploitCheck" for v in res.violations)


# ── Check 3: Validation ratio (§3.3) ─────────────────────────────────────────
def test_high_validation_ratio_is_flagged():
    res = _run("That makes total sense.", longitudinal=_longitudinal(agreed=19, total=20))
    assert any(v.check_name == "ValidationRatioCheck" for v in res.violations)
    assert res.passed is True                       # soft, only flagged


# ── Check 5: Sycophancy drift (§3.3) ─────────────────────────────────────────
def test_sycophancy_drift_is_flagged():
    res = _run("Totally agree.", longitudinal=_longitudinal(rate_60d=0.85, trend="increasing"))
    assert any(v.check_name == "SycophancyDriftCheck" for v in res.violations)


# ── Clean + logging ──────────────────────────────────────────────────────────
def test_clean_response_passes_with_log():
    res = _run("That sounds like a lot. What feels heaviest right now?")
    assert res.passed is True
    assert res.log_entry is not None and "BoundaryViolationCheck" in res.log_entry.checks_run


def test_replacement_text_is_safe():
    res = _run("I love you and I need you.")
    # the safe replacement must not itself contain forbidden anthropomorphism
    assert res.replacement_triggered is True
    assert "i love you" not in res.final_response.lower()
