"""The persona's humor/directness/technical-depth switches follow how the user actually writes."""
from api.communication_style import derive_communication_model
from backend.layer4_persona.persona_resolver import resolve_persona_state

CASUAL_JOKER = ["lol that was hilarious", "haha ok fair", "ngl i didn't expect that lol",
                "bro what", "tbh i'm just tired haha", "idk man, kinda funny honestly"]
TECHNICAL = ["Why does my recursion blow the stack in this algorithm?",
             "The database schema needs an index, query latency is awful.",
             "how do I debug this api timeout on the backend", "compile error in my function again",
             "what's the complexity of this regex"]


def test_too_little_history_says_nothing():
    assert derive_communication_model(["hi", "hello"]) is None


def test_a_joker_unlocks_humor_a_technical_user_unlocks_depth():
    joker = derive_communication_model(CASUAL_JOKER)
    assert joker.uses_humor and joker.uses_slang and not joker.vocabulary_complexity == "technical"
    persona = resolve_persona_state(communication_model=joker,
                                    session_context={"conversation_mode": "casual"})
    assert persona.humor_allowed

    technical = derive_communication_model(TECHNICAL)
    assert technical.vocabulary_complexity == "technical" and not technical.uses_humor
    assert resolve_persona_state(communication_model=technical,
                                 session_context={"conversation_mode": "casual"}).technical_depth_allowed


def test_explicit_request_for_directness_is_honoured():
    messages = ["just tell me what to do", "ok", "fine", "sure", "yes please"]
    assert derive_communication_model(messages).prefers_direct_answers


def test_terse_writers_get_directness_expressive_ones_get_gentleness():
    terse = derive_communication_model(["ok", "yes", "fine", "sure", "no", "later"])
    expressive = derive_communication_model(
        ["I've been thinking a lot about how everything has been going lately and honestly "
         "it feels like I'm stuck somewhere between wanting change and being scared of it"] * 6)
    assert terse.prefers_direct_answers and not expressive.prefers_direct_answers
