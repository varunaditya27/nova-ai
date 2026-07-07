"""Layer-13 per-turn active elicitation: trigger-gated, one-per-session, never repeated."""
from api.elicitation import detect_triggers, select_elicitation


def test_first_session_greeting_surfaces_the_name_question():
    item = select_elicitation("hi there!", session_number=1, surfaced_targets=[],
                              asked_this_session=False)
    assert item is not None and item.inference_target == "user_handle"
    assert item.question and "call you" in item.question


def test_studying_mention_surfaces_life_phase():
    item = select_elicitation("ugh so much studying for my exam", session_number=2,
                              surfaced_targets=["user_handle"], asked_this_session=False)
    assert item is not None and item.inference_target == "life_phase"


def test_already_surfaced_target_is_not_repeated():
    # Only life_phase would match, but it's already surfaced → nothing to ask.
    item = select_elicitation("more studying for the exam", session_number=5,
                              surfaced_targets=["user_handle", "life_phase"], asked_this_session=False)
    assert item is None


def test_rate_limited_when_already_asked_this_session():
    assert select_elicitation("hi", session_number=1, surfaced_targets=[],
                              asked_this_session=True) is None


def test_no_trigger_no_question():
    assert select_elicitation("the sky is a nice colour", session_number=6,
                              surfaced_targets=[], asked_this_session=False) is None


def test_distress_suppresses_nice_to_have_priority3():
    # A goals mention (priority 3) must not surface amid clear distress.
    item = select_elicitation("i want to do something but i feel so hopeless and worthless",
                              session_number=6, surfaced_targets=["user_handle", "life_phase",
                              "primary_reason"], asked_this_session=False)
    assert item is None


def test_session_position_triggers():
    assert "end_of_first_exchange" in detect_triggers("anything", 1)
    assert "session_2_or_3_any_reflective_moment" in detect_triggers("anything", 3)
