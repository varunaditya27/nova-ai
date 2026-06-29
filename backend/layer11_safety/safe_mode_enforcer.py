"""Safe Mode Enforcer — crisis output hard override (architecture doc §5.2).

When crisis mode is active, the response must be plain prose: no markdown, no lists, no emoji, no
embellishment, and bounded in length. This is the Layer 11 hard override that Layer 9 honors —
it strips anything that could read as scattered or dismissive in a crisis moment. Deterministic.
"""

from __future__ import annotations

import re
from typing import Optional

from backend.layer11_safety.schemas import CrisisModeConstraints

_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\s)(.+?)\*")
_HR_RE = re.compile(r"^-{3,}$", re.MULTILINE)
_EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF" "️" "]+", flags=re.UNICODE)


def enforce_safe_mode(response_text: str, constraints: Optional[CrisisModeConstraints] = None) -> str:
    """Strip formatting/emoji and bound length for a crisis response (architecture doc §5.2)."""
    if not response_text:
        return ""
    text = response_text
    text = _HEADER_RE.sub("", text)
    text = _BULLET_RE.sub("", text)
    text = _NUMBERED_RE.sub("", text)
    text = _HR_RE.sub("", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n+ *", " ", text).strip()

    max_words = (constraints or CrisisModeConstraints()).max_response_length_words
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text
