"""Tests for SC-4 Format Adapter (architecture doc §6)."""

from backend.layer9_output import format_adapter as fa
from backend.layer9_output.schemas import (
    CodeFormat,
    EmojiPolicy,
    FormatSpec,
    Register,
    Structure,
    UserFormatProfile,
)


def _profile(**kw):
    return UserFormatProfile(user_id="u1", **kw)


def _spec(mode="casual_chat", content_type="general", stage="friend", intensity=0.2,
          voice=False, profile=None, crisis=False, num_entities=0):
    return fa.compute_format_spec(
        conversation_mode=mode, content_type=content_type, relationship_stage=stage,
        emotional_intensity=intensity, voice_mode=voice,
        user_format_profile=profile or _profile(), crisis_mode_active=crisis,
        num_entities=num_entities)


# ── Crisis override (§6.3) ───────────────────────────────────────────────────
def test_crisis_forces_pure_prose_no_emoji():
    s = _spec(mode="crisis_support", crisis=True)
    assert s.structure == Structure.PURE_PROSE.value
    assert s.emoji_policy == EmojiPolicy.NONE.value
    assert s.allow_headers is False and s.allow_bold is False
    assert s.crisis_mode_active is True


# ── Register by relationship stage (§6.3) ────────────────────────────────────
def test_stranger_is_formal_no_contractions():
    s = _spec(stage="stranger")
    assert s.register == Register.FORMAL.value and s.use_contractions is False


def test_friend_is_intimate_with_contractions():
    s = _spec(stage="friend")
    assert s.register == Register.INTIMATE.value and s.use_contractions is True


# ── Structure (§6.3) ─────────────────────────────────────────────────────────
def test_emotional_support_is_pure_prose():
    s = _spec(mode="emotional_support", intensity=0.8)
    assert s.structure == Structure.PURE_PROSE.value and s.max_list_items == 0


def test_high_emotional_intensity_forces_prose_even_in_casual():
    s = _spec(mode="casual_chat", intensity=0.8)
    assert s.structure == Structure.PURE_PROSE.value


def test_instructional_content_is_structured_list():
    s = _spec(mode="task_help", content_type="step_by_step", intensity=0.1)
    assert s.structure == Structure.STRUCTURED_LIST.value and s.max_list_items > 0


def test_comparative_with_many_entities_is_table():
    s = _spec(mode="task_help", content_type="comparative_analysis", intensity=0.1, num_entities=4)
    assert s.structure == Structure.TABLE.value


# ── Emoji policy (§6.3) ──────────────────────────────────────────────────────
def test_celebration_allows_natural_emoji():
    s = _spec(mode="celebration", intensity=0.3)
    assert s.emoji_policy == EmojiPolicy.NATURAL.value and s.max_emojis_per_message >= 1


def test_technical_has_no_emoji():
    s = _spec(mode="technical", content_type="code_help", intensity=0.1)
    assert s.emoji_policy == EmojiPolicy.NONE.value


def test_emoji_mirrors_user_rate_for_friends():
    none = _spec(stage="friend", profile=_profile(emoji_usage_rate=0.0))
    natural = _spec(stage="friend", profile=_profile(emoji_usage_rate=0.4))
    assert none.emoji_policy == EmojiPolicy.NONE.value
    assert natural.emoji_policy == EmojiPolicy.NATURAL.value


# ── Code formatting (§6.3) ───────────────────────────────────────────────────
def test_code_help_uses_full_blocks():
    s = _spec(mode="technical", content_type="code_help", intensity=0.1)
    assert s.code_format == CodeFormat.FULL_BLOCKS.value and s.language_label_required is True


# ── Voice transform flag (§6.3) ──────────────────────────────────────────────
def test_voice_with_structure_requires_transform():
    s = _spec(mode="task_help", content_type="step_by_step", intensity=0.1, voice=True)
    assert s.voice_content_transform_required is True


# ── Post-generation enforcement (§6.4) ───────────────────────────────────────
def test_enforce_strips_markdown_in_pure_prose():
    spec = FormatSpec(structure=Structure.PURE_PROSE.value, emoji_policy=EmojiPolicy.NONE.value)
    out = fa.enforce_format_spec("## Heading\n- bullet one\n**bold** text", spec)
    assert "##" not in out and "**" not in out and "- bullet" not in out


def test_enforce_removes_emoji_when_policy_none():
    spec = FormatSpec(structure=Structure.PROSE_WITH_BREAKS.value,
                      emoji_policy=EmojiPolicy.NONE.value)
    out = fa.enforce_format_spec("nice work 🎉 well done 😀", spec)
    assert "🎉" not in out and "😀" not in out
