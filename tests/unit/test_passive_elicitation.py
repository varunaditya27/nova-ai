"""Tests for SC-1 Passive Elicitation Engine — 8 extractors (architecture doc §4.5)."""

from datetime import datetime
from types import SimpleNamespace

from backend.layer13_onboarding import passive_elicitation as pe
from backend.layer13_onboarding.schemas import PassiveSignalBundle

NOW = datetime(2025, 6, 1, 14, 0)


def _turn(text):
    return SimpleNamespace(user_message=text)


def _engine():
    return pe.PassiveElicitationEngine()


# ── Orchestrator (§4.5) ──────────────────────────────────────────────────────
def test_extract_returns_full_bundle():
    bundle = _engine().extract("hey there", message_index=0, session_number=1,
                               timestamp=NOW, session_history=[])
    assert isinstance(bundle, PassiveSignalBundle)


def test_extract_is_exception_safe_per_extractor():
    # A broken extractor must be skipped without corrupting the rest of the bundle.
    eng = _engine()
    eng._extract_urgency = lambda message: (_ for _ in ()).throw(RuntimeError("boom"))
    bundle = eng.extract("I'm anxious", message_index=0, session_number=1,
                         timestamp=NOW, session_history=[])
    assert isinstance(bundle, PassiveSignalBundle)
    assert bundle.emotional_expression_style.style == "direct"   # other extractors still ran


# ── Extractor 1: vocabulary register ─────────────────────────────────────────
def test_vocabulary_detects_informality_and_emoji():
    vr = _engine()._extract_vocabulary_register("ngl this is kinda fun 😄")
    assert vr.formality_delta < 0
    assert vr.uses_emoji is True


def test_vocabulary_detects_formality():
    vr = _engine()._extract_vocabulary_register(
        "Therefore, regarding the matter, I would consequently proceed.")
    assert vr.formality_delta > 0


# ── Extractor 2: emotional expression style ──────────────────────────────────
def test_emotional_style_direct():
    es = _engine()._extract_emotional_style("I'm really anxious about this", [])
    assert es.style == "direct"


def test_emotional_style_indirect():
    es = _engine()._extract_emotional_style("it's just been a weird week, kind of off", [])
    assert es.style == "indirect"


# ── Extractor 3: topic approach ──────────────────────────────────────────────
def test_topic_approach_seeks_opinion_and_hedges():
    ta = _engine()._extract_topic_approach("I might be wrong but what do you think?", [])
    assert ta.seeks_opinions is True and ta.hedges_views is True


# ── Extractor 4: self-disclosure comfort ─────────────────────────────────────
def test_disclosure_high_when_personal():
    dc = _engine()._extract_disclosure_comfort("I feel like my family problem is dealing with me", [])
    assert dc.level in ("medium", "high") and dc.density > 0


def test_disclosure_low_when_impersonal():
    dc = _engine()._extract_disclosure_comfort("what is the capital of France", [])
    assert dc.level == "low"


# ── Extractor 5: named people ────────────────────────────────────────────────
def test_named_people_with_relationship_context():
    people = _engine()._extract_named_people("my friend Arjun came over")
    assert len(people) == 1
    assert people[0].name == "Arjun" and people[0].relationship_type == "friend"


# ── Extractor 6: life context ────────────────────────────────────────────────
def test_life_context_student():
    lc = _engine()._extract_life_context("I have an exam and an assignment on campus")
    assert lc.life_phase_signal == "student" and lc.life_phase_confidence > 0


def test_life_context_working():
    lc = _engine()._extract_life_context("my manager set a deadline at the office")
    assert lc.life_phase_signal == "working"


# ── Extractor 7: urgency ─────────────────────────────────────────────────────
def test_urgency_high():
    assert _engine()._extract_urgency("I need to know now, this is urgent").level == "high"


def test_urgency_low_exploratory():
    assert _engine()._extract_urgency("just wondering, no rush").level == "low"


# ── Extractor 8: communication style (verbosity) ─────────────────────────────
def test_communication_style_concise():
    cs = _engine()._extract_communication_style("yeah ok", [])
    assert cs.verbosity_preference == "concise"


def test_communication_style_uses_history():
    hist = [_turn("a " * 80), _turn("b " * 80)]
    cs = _engine()._extract_communication_style("c " * 80, hist)
    assert cs.verbosity_preference == "verbose" and cs.sample_count == 3
