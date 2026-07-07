"""Per-user persona-param learning (Layer 4/5): observe style, nudge params, emit a directive."""
from backend.layer4_persona.schemas import RelationshipState
from backend.layer4_persona.style_learning import learn_communication_style, persona_style_directive


def test_short_messages_pull_verbosity_down():
    st = RelationshipState()  # response_length_preference defaults 0.5
    for _ in range(6):
        learn_communication_style(st, "ok")
    assert st.response_length_preference < 0.35


def test_long_messages_pull_verbosity_up():
    st = RelationshipState()
    long_msg = "I've been thinking a lot about this and there's really so much going on. " * 5
    for _ in range(6):
        learn_communication_style(st, long_msg)
    assert st.response_length_preference > 0.65


def test_casual_register_learned():
    st = RelationshipState()
    for _ in range(6):
        learn_communication_style(st, "lol yeah gonna hang out, u wanna come?")
    assert st.formality_preference < 0.4


def test_formal_register_learned():
    st = RelationshipState()
    for _ in range(6):
        learn_communication_style(st, "Regarding the matter, I shall proceed; furthermore, kindly advise.")
    assert st.formality_preference > 0.6


def test_advice_seeking_raises_advice_tolerance():
    st = RelationshipState()
    for _ in range(6):
        learn_communication_style(st, "what should I do about my schedule? any tips?")
    assert st.unsolicited_advice_tolerance > 0.6


def test_empty_message_is_a_noop():
    st = RelationshipState()
    learn_communication_style(st, "")
    assert st.response_length_preference == 0.5


def test_directive_is_plain_language_no_scores():
    st = RelationshipState(response_length_preference=0.15, formality_preference=0.15)
    d = persona_style_directive(st)
    assert "short" in d and "casual" in d
    assert "0.1" not in d and "preference" not in d.lower()   # no raw scores leak


def test_neutral_state_yields_no_directive():
    assert persona_style_directive(RelationshipState()) == ""
