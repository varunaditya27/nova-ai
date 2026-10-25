"""Tests for SC-1 Short-Term Memory buffer eviction + promotion (architecture doc §3)."""

from datetime import datetime
from uuid import uuid4

from backend.layer2_memory import stm
from backend.layer2_memory.schemas import (
    ConversationTurn,
    EmotionVector,
    ShortTermMemoryBuffer,
)


def _buffer(max_turns=40, char_limit=12000):
    return ShortTermMemoryBuffer(session_id=uuid4(), user_id=uuid4(),
                                 max_turns=max_turns, char_limit=char_limit)


def _turn(content="hi", **kw):
    return ConversationTurn(content=content, timestamp=datetime(2026, 6, 26), **kw)


def test_add_turn_tracks_char_count():
    buf = _buffer()
    stm.add_turn(buf, _turn("hello"))
    assert buf.total_chars == 5
    assert len(buf.turns) == 1


def test_eviction_by_max_turns_returns_oldest():
    buf = _buffer(max_turns=2)
    stm.add_turn(buf, _turn("first"))
    stm.add_turn(buf, _turn("second"))
    evicted = stm.add_turn(buf, _turn("third"))
    assert len(buf.turns) == 2
    assert [t.content for t in buf.turns] == ["second", "third"]
    assert [t.content for t in evicted] == ["first"]


def test_eviction_by_char_limit():
    buf = _buffer(char_limit=10)
    stm.add_turn(buf, _turn("aaaaa"))   # 5
    evicted = stm.add_turn(buf, _turn("bbbbbbbb"))  # 8 → total 13 > 10
    assert [t.content for t in evicted] == ["aaaaa"]
    assert buf.total_chars == 8


def test_promotion_importance_flag():
    assert stm.should_promote(_turn(importance_flag=True)) is True


def test_promotion_high_arousal():
    t = _turn(emotional_annotation=EmotionVector(valence=-0.5, arousal=0.7))
    assert stm.should_promote(t) is True


def test_no_promotion_low_arousal_casual():
    t = _turn("lol nice", emotional_annotation=EmotionVector(valence=0.2, arousal=0.2))
    assert stm.should_promote(t) is False


def test_promotion_life_event_keyword():
    assert stm.should_promote(_turn("I finally got the job at Infosys!")) is True


def test_calm_personal_disclosure_is_promoted_but_chatter_and_questions_are_not():
    assert stm.should_promote(_turn("I'm vegetarian and I live in Pune with my cousin")) is True
    assert stm.should_promote(_turn("my sister Meera is visiting us next week from Delhi")) is True
    assert stm.should_promote(_turn("what do you think I should have for dinner tonight?")) is False
    assert stm.should_promote(_turn("ok thanks, that makes sense to me now")) is False
    assert stm.should_promote(_turn("I'm good")) is False
