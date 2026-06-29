"""Tests for the Safe Mode Enforcer — crisis output hard override (architecture doc §5.2)."""

from backend.layer11_safety import safe_mode_enforcer as sme
from backend.layer11_safety.schemas import CrisisModeConstraints


def test_strips_markdown_to_prose():
    out = sme.enforce_safe_mode("## Heading\n- a bullet\n**bold** and more")
    assert "##" not in out and "**" not in out and "- a bullet" not in out


def test_removes_emoji():
    out = sme.enforce_safe_mode("I'm here with you 💙 you're not alone 🙏")
    assert "💙" not in out and "🙏" not in out


def test_plain_prose_is_unchanged_in_substance():
    text = "I hear you. Are you safe right now?"
    assert sme.enforce_safe_mode(text) == text


def test_enforces_max_word_length():
    long_text = " ".join(["word"] * 200)
    out = sme.enforce_safe_mode(long_text, constraints=CrisisModeConstraints(max_response_length_words=120))
    assert len(out.split()) <= 120


def test_returns_string_for_empty():
    assert isinstance(sme.enforce_safe_mode(""), str)
