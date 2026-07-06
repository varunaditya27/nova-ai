"""Robust JSON extraction from real-LLM output (pure stdlib).

Local models routinely wrap JSON in ```json fences or add a sentence of preamble, which breaks a
naive ``json.loads``. ``extract_json`` returns a clean JSON string: it strips markdown fences and,
failing a direct parse, slices out the first balanced ``{...}`` / ``[...]`` object. Applied at the
adapter boundary so each Layer's own ``json.loads`` receives parseable text.
"""
from __future__ import annotations

import json
import re

_FENCE_OPEN = re.compile(r"^```[a-zA-Z0-9]*\s*")
_FENCE_CLOSE = re.compile(r"\s*```$")


def extract_json(text: str) -> str:
    if not text:
        return text
    s = text.strip()
    if s.startswith("```"):
        s = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", s)).strip()
    try:
        json.loads(s)
        return s
    except Exception:
        pass
    # Slice the first balanced JSON object/array out of surrounding prose.
    start = next((i for i, ch in enumerate(s) if ch in "{["), None)
    if start is None:
        return s
    open_ch = s[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    for j in range(start, len(s)):
        if s[j] == open_ch:
            depth += 1
        elif s[j] == close_ch:
            depth -= 1
            if depth == 0:
                return s[start:j + 1]
    return s[start:]
