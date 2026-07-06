"""SSE streaming of a finished, guardrailed turn via Layer-9 typing overlay."""
import json
import random

import pytest
pytest.importorskip("pydantic")

from types import SimpleNamespace

from backend.layer9_output.stream_typing_overlay import StreamTypingOverlay
from api.streaming import stream_turn, _tokenize, _MODE_TO_TYPING


class FakeOrchestrator:
    def __init__(self, text, mode="casual", system="system1"):
        self._out = SimpleNamespace(
            response_text=text, delivered=text, conversation_mode=mode,
            cognitive_system=system, crisis_active=False, refined=False,
            confabulation_guard=False)
    def run_turn(self, user_id, message, now=None, session_id=""):
        self.seen = (user_id, message, session_id)
        return self._out


def _parse_sse(chunks):
    events = []
    for raw in "".join(chunks).split("\n\n"):
        raw = raw.strip()
        if not raw:
            continue
        name = next(l[len("event:"):].strip() for l in raw.splitlines() if l.startswith("event:"))
        data = next(l[len("data:"):].strip() for l in raw.splitlines() if l.startswith("data:"))
        events.append((name, json.loads(data)))
    return events


def test_tokenize_is_lossless():
    text = "Hello there. How are you?"
    assert "".join(_tokenize(text)) == text


def test_stream_emits_meta_tokens_done_and_reconstructs_text():
    text = "Hey there. Good to see you!"
    orch = FakeOrchestrator(text)
    chunks = list(stream_turn(orch, StreamTypingOverlay(), "local-user", "hi",
                              session_id="s1", rng=random.Random(0)))
    events = _parse_sse(chunks)

    assert events[0][0] == "meta"
    assert events[0][1]["session_id"] == "s1"
    assert events[-1][0] == "done"

    tokens = [e for e in events if e[0] == "token"]
    assert len(tokens) == len(_tokenize(text))
    assert "".join(t[1]["token"] for t in tokens) == text
    assert all(t[1]["delay_ms"] >= 20 for t in tokens)  # overlay floor


def test_stream_emits_error_frame_when_turn_fails():
    """A failure in the turn/pacing must surface as a terminal `error` SSE frame, not a silently
    truncated stream — the frontend needs a clean, handleable signal."""
    class BoomOrchestrator:
        def run_turn(self, user_id, message, now=None, session_id=""):
            raise RuntimeError("turn exploded")

    chunks = list(stream_turn(BoomOrchestrator(), StreamTypingOverlay(), "local-user", "hi",
                              session_id="s1", rng=random.Random(0)))
    events = _parse_sse(chunks)
    assert events and events[-1][0] == "error"
    assert events[-1][1]["session_id"] == "s1"


def test_mode_map_covers_l3_modes():
    for m in ("casual", "emotional_support", "crisis", "technical_discussion",
              "goal_planning", "life_review", "social_coaching", "celebration"):
        assert m in _MODE_TO_TYPING
