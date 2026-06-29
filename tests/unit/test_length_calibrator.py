"""Tests for SC-1 Length Calibrator (architecture doc §3.6)."""

from backend.layer9_output import length_calibrator as lc


def _target(mode="casual_chat", intensity=0.2, content="general", turn="casual",
            stage="friend", pref="medium"):
    return lc.compute_length_target(
        conversation_mode=mode, emotional_intensity=intensity, content_type=content,
        turn_type=turn, relationship_stage=stage, user_preferred_length=pref)


def test_casual_base_range():
    assert _target(mode="casual_chat") == (40, 180)


def test_venting_caps_max_length():
    _, max_c = _target(mode="deep_reasoning", turn="venting")
    assert max_c == 200


def test_question_caps_max_length():
    _, max_c = _target(mode="deep_reasoning", turn="question")
    assert max_c == 180


def test_high_emotion_shortens_max():
    _, calm = _target(mode="deep_reasoning", intensity=0.2)
    _, intense = _target(mode="deep_reasoning", intensity=0.8)
    assert intense < calm


def test_stranger_raises_min():
    min_c, _ = _target(mode="casual_chat", stage="stranger")
    assert min_c >= 100


def test_close_friend_lowers_min():
    min_c, _ = _target(mode="task_help", stage="close_friend")
    base_min, _ = _target(mode="task_help", stage="friend")
    assert min_c < base_min


def test_user_short_preference_shrinks_max():
    _, short = _target(mode="deep_reasoning", pref="short")
    _, medium = _target(mode="deep_reasoning", pref="medium")
    assert short < medium


def test_user_long_preference_grows_max():
    _, long = _target(mode="deep_reasoning", pref="long")
    _, medium = _target(mode="deep_reasoning", pref="medium")
    assert long > medium


def test_max_is_capped_at_1200():
    _, max_c = _target(mode="deep_reasoning", pref="long")
    assert max_c <= 1200
