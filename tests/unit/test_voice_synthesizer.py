"""Tests for SC-3 Voice & SSML Synthesizer (architecture doc §5.2-§5.6)."""

from backend.layer9_output import voice_synthesizer as vs
from backend.layer9_output.schemas import AudioResult, SSMLDocument


class _Rng:
    def __init__(self, r=0.0):
        self._r = r
    def random(self):
        return self._r
    def choice(self, seq):
        return seq[0]


class _Backend:
    def __init__(self, ok=True):
        self._ok = ok
        self.last_ssml = None
    def synthesize(self, ssml_text, voice_id=None):
        self.last_ssml = ssml_text
        return AudioResult(audio_bytes=b"A", ok=True) if self._ok else AudioResult(ok=False,
                                                                                   error="down")


# ── SSML generation (§5.2) ───────────────────────────────────────────────────
def test_generate_ssml_wraps_in_speak_and_prosody():
    doc = vs.generate_ssml("Hello there.", conversation_mode="casual_chat")
    assert isinstance(doc, SSMLDocument)
    assert doc.ssml.strip().startswith("<speak>") and "<prosody" in doc.ssml


# ── Prosody table (§5.3) ─────────────────────────────────────────────────────
def test_prosody_emotional_support_is_slow_and_lower():
    p = vs.compute_prosody_params("emotional_support")
    assert p.rate == "slow" and p.pitch.startswith("-")


def test_prosody_celebration_is_faster_and_higher():
    p = vs.compute_prosody_params("celebration")
    assert p.rate == "medium-fast" and p.pitch.startswith("+")


def test_prosody_crisis_is_x_slow():
    assert vs.compute_prosody_params("crisis_support").rate == "x-slow"


# ── Break annotation (§5.4) ──────────────────────────────────────────────────
def test_annotate_breaks_inserts_break_at_sentence_boundary():
    out = vs.annotate_breaks("One thing. Another thing.", "casual_chat")
    assert "<break" in out


# ── Filler policy (§5.5) ─────────────────────────────────────────────────────
def test_no_fillers_in_technical():
    text = "First sentence. Second sentence."
    assert vs.inject_fillers(text, "technical", rng=_Rng(0.0)) == text


def test_fillers_injected_when_rate_met():
    out = vs.inject_fillers("First sentence. Second sentence.", "casual_chat", rng=_Rng(0.0))
    assert out != "First sentence. Second sentence."


# ── Voice content transforms (§5.6) ──────────────────────────────────────────
def test_bold_becomes_emphasis():
    assert "<emphasis" in vs.apply_voice_content_transforms("this is **important** stuff")


def test_bullets_become_spoken_enumeration():
    out = vs.apply_voice_content_transforms("- apples\n- oranges")
    assert "First" in out and "apples" in out


# ── Synthesis dispatch + fallback (§5.7, §9) ─────────────────────────────────
def test_synthesize_calls_backend_with_ssml():
    backend = _Backend(ok=True)
    res = vs.synthesize("Hello.", backend=backend, conversation_mode="casual_chat")
    assert res.ok is True and backend.last_ssml and "<speak>" in backend.last_ssml


def test_synthesize_without_backend_is_graceful():
    res = vs.synthesize("Hello.", backend=None, conversation_mode="casual_chat")
    assert res.ok is False


def test_synthesize_backend_failure_is_graceful():
    res = vs.synthesize("Hello.", backend=_Backend(ok=False), conversation_mode="casual_chat")
    assert res.ok is False


def test_generate_ssml_is_well_formed_when_the_reply_contains_markup_characters():
    import xml.etree.ElementTree as ET
    doc = vs.generate_ssml("Tom & Jerry: 5 < 6, but 7 > 3. It is <3.", "casual_chat")
    spoken = "".join(ET.fromstring(doc.ssml).itertext())
    assert "Tom & Jerry" in spoken and "5 < 6" in spoken
