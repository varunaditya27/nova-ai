"""Derive the user's CommunicationModel from how they actually write (docs/layer-2 §7.6).

Feeds Layer 4's persona resolver — whether humor, directness and technical depth are open to Nova —
which were constant in production because nothing ever produced the model. Deterministic and
read-only over the permanent message log (no LLM call). It is passed to ``resolve_persona_state``
only, never to ``compute_relationship_state``, whose style-calibration step would overwrite the
EMA-learned params ``style_learning.py`` owns.
"""
from __future__ import annotations

import re
from statistics import median

from backend.layer2_memory.schemas import CommunicationModel
from infra.db.message_store import PostgresMessageStore

_MIN_MESSAGES = 5
_WINDOW = 40
_HUMOR = re.compile(r"\b(lol|lmao|haha+|hehe+|rofl|jk)\b|[😂🤣😆😄😜]", re.IGNORECASE)
_SLANG = re.compile(r"\b(ngl|tbh|idk|imo|bro|gonna|wanna|gotta|kinda|nvm|omg)\b", re.IGNORECASE)
_DIRECT = re.compile(r"\b(just tell me|be direct|straight up|to the point|tl;?dr|bottom line|"
                     r"don'?t sugarcoat)\b", re.IGNORECASE)
_TECHNICAL = re.compile(r"\b(algorithm|api|database|function|compile[rd]?|debug|server|backend|"
                        r"frontend|recursion|complexity|stack|latency|schema|regex|theorem|"
                        r"derivative|integral|circuit|kernel)\b", re.IGNORECASE)
_SHARE_FOR_TRAIT = 0.15


def derive_communication_model(messages: list[str]):
    """None until there are enough messages to say anything honest about the user's style."""
    if len(messages) < _MIN_MESSAGES:
        return None
    share = lambda pattern: sum(1 for m in messages if pattern.search(m)) / len(messages)
    words = median(len(m.split()) for m in messages)
    return CommunicationModel(
        vocabulary_complexity="technical" if share(_TECHNICAL) >= _SHARE_FOR_TRAIT else "moderate",
        typical_message_length="short" if words < 8 else "long" if words > 25 else "moderate",
        uses_slang=share(_SLANG) >= _SHARE_FOR_TRAIT,
        uses_humor=share(_HUMOR) >= _SHARE_FOR_TRAIT,
        # Terse writers want terse, direct answers; expressive ones are met more gently.
        prefers_direct_answers=any(_DIRECT.search(m) for m in messages) or words < 8,
        sessions_used_for_calibration=len(messages))


def make_communication_model_provider(session_factory):
    def _provider(user_id):
        rows = PostgresMessageStore(session_factory, user_id).history(limit=_WINDOW * 2)
        return derive_communication_model(
            [r["content"] for r in rows if r["role"] == "user"][:_WINDOW])
    return _provider
