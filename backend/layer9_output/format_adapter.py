"""SC-4 — Format Adapter (architecture doc §6).

Decides the format of every response *before* Layer 4 generates it (register, structure,
length target, markdown, emoji, code), and enforces it post-generation as a hard backstop.
Fully deterministic — no LLM, no I/O. Format follows relationship before content (§11.3), and
emotional/crisis content is always pure prose.
"""

from __future__ import annotations

import re

from backend.layer9_output.schemas import (
    CodeFormat,
    EmojiPolicy,
    FormatSpec,
    Register,
    Structure,
    UserFormatProfile,
)

# Markdown patterns stripped when structure == pure_prose (§6.4).
_HEADER_RE = re.compile(r"^#{1,4}\s+", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_HR_RE = re.compile(r"^---+$", re.MULTILINE)

# Emoji range (broad; covers the common pictographic blocks).
_EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF" "\U00002B00-\U00002BFF" "️" "]+",
    flags=re.UNICODE,
)


def compute_format_spec(
    conversation_mode: str,
    content_type: str,
    relationship_stage: str,
    emotional_intensity: float,
    voice_mode: bool,
    user_format_profile: UserFormatProfile,
    crisis_mode_active: bool = False,
    num_entities: int = 0,
) -> FormatSpec:
    """Build a FormatSpec from context (architecture doc §6.3)."""
    profile = user_format_profile or UserFormatProfile()

    # CRISIS MODE: absolute override (§6.3).
    if crisis_mode_active:
        return FormatSpec(
            register=Register.INTIMATE.value, use_contractions=True, allow_fragments=True,
            structure=Structure.PURE_PROSE.value, max_list_items=0, allow_headers=False,
            allow_bold=False, emoji_policy=EmojiPolicy.NONE.value, max_emojis_per_message=0,
            code_format=CodeFormat.NONE.value, voice_mode=voice_mode,
            voice_content_transform_required=False, crisis_mode_active=True)

    # --- REGISTER ---
    if relationship_stage == "stranger":
        register, use_contractions, allow_fragments, allow_slang = (
            Register.FORMAL.value, False, False, False)
    elif relationship_stage == "acquaintance":
        register, use_contractions, allow_fragments, allow_slang = (
            Register.CASUAL.value, True, False, False)
    else:  # friend, close_friend
        register, use_contractions, allow_fragments = Register.INTIMATE.value, True, True
        allow_slang = profile.uses_slang_themselves

    # --- STRUCTURE ---
    if conversation_mode in ("emotional_support", "crisis_support") or emotional_intensity > 0.65:
        structure, max_list_items, allow_headers, allow_bold = (
            Structure.PURE_PROSE.value, 0, False, False)
    elif conversation_mode == "casual_chat":
        structure, max_list_items, allow_headers, allow_bold = (
            Structure.PROSE_WITH_BREAKS.value, 0, False, False)
    elif content_type in ("comparative_analysis", "multiple_options"):
        structure = Structure.TABLE.value if num_entities >= 3 else Structure.STRUCTURED_LIST.value
        max_list_items, allow_headers, allow_bold = 6, True, True
    elif content_type in ("instructional", "step_by_step"):
        structure, max_list_items = Structure.STRUCTURED_LIST.value, 8
        allow_headers, allow_bold = conversation_mode == "task_help", True
    elif conversation_mode == "deep_reasoning":
        structure, max_list_items, allow_headers, allow_bold = (
            Structure.PROSE_WITH_BREAKS.value, 3, False, True)
    else:
        structure, max_list_items, allow_headers, allow_bold = (
            Structure.PROSE_WITH_BREAKS.value, 3, False, False)

    # --- EMOJI POLICY ---
    if register == Register.FORMAL.value or conversation_mode in (
            "technical", "task_help", "crisis_support"):
        emoji_policy, max_emojis = EmojiPolicy.NONE.value, 0
    elif conversation_mode == "celebration":
        emoji_policy, max_emojis = EmojiPolicy.NATURAL.value, 2
    elif relationship_stage in ("friend", "close_friend"):
        if profile.emoji_usage_rate < 0.05:
            emoji_policy, max_emojis = EmojiPolicy.NONE.value, 0
        elif profile.emoji_usage_rate < 0.20:
            emoji_policy, max_emojis = EmojiPolicy.RARE.value, 1
        else:
            emoji_policy, max_emojis = EmojiPolicy.NATURAL.value, 1
    else:
        emoji_policy, max_emojis = EmojiPolicy.NONE.value, 0

    # --- CODE FORMATTING ---
    if content_type in ("technical", "code_help", "debugging"):
        code_format, language_label_required = CodeFormat.FULL_BLOCKS.value, True
    elif content_type == "technical_casual":
        code_format, language_label_required = CodeFormat.INLINE_ONLY.value, False
    else:
        code_format, language_label_required = CodeFormat.NONE.value, False

    # --- EXPLICIT USER OVERRIDES (highest priority) ---
    if profile.prefers_no_markdown:
        allow_headers = allow_bold = False
    if profile.prefers_bullets and structure != Structure.PURE_PROSE.value:
        structure = Structure.STRUCTURED_LIST.value
        max_list_items = max(max_list_items, 5)

    return FormatSpec(
        register=register, use_contractions=use_contractions, allow_fragments=allow_fragments,
        allow_slang=allow_slang, structure=structure, max_list_items=max_list_items,
        allow_headers=allow_headers, allow_bold=allow_bold, emoji_policy=emoji_policy,
        max_emojis_per_message=max_emojis, code_format=code_format,
        language_label_required=language_label_required, voice_mode=voice_mode,
        voice_content_transform_required=(voice_mode and structure != Structure.PURE_PROSE.value),
        crisis_mode_active=False)


def enforce_format_spec(text: str, format_spec: FormatSpec) -> str:
    """Post-generation backstop: strip disallowed formatting (architecture doc §6.4)."""
    if format_spec.structure == Structure.PURE_PROSE.value:
        text = _HEADER_RE.sub("", text)
        text = _BULLET_RE.sub("", text)
        text = _NUMBERED_RE.sub("", text)
        text = _HR_RE.sub("", text)
        text = _BOLD_RE.sub(r"\1", text)
    elif not format_spec.allow_bold:
        text = _BOLD_RE.sub(r"\1", text)

    if format_spec.emoji_policy == EmojiPolicy.NONE.value:
        text = _EMOJI_RE.sub("", text)
    else:
        text = _reduce_emoji_to_limit(text, format_spec.max_emojis_per_message)
    return _tidy_whitespace(text)


def _reduce_emoji_to_limit(text: str, limit: int) -> str:
    if limit <= 0:
        return _EMOJI_RE.sub("", text)
    seen = 0

    def _keep(match):
        nonlocal seen
        kept = []
        for ch in match.group(0):
            if seen < limit:
                kept.append(ch)
                seen += 1
        return "".join(kept)

    return _EMOJI_RE.sub(_keep, text)


def _tidy_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n", "\n", text)
    return text.strip()
