"""Tools fire on requests addressed to Nova, never on emotional disclosures that merely contain a
keyword ("my meeting stresses me out", "that song reminded me of my dad")."""
import pytest

from backend.layer8_tools.intent_routing import keyword_route

REQUESTS = [
    ("search for puppy training tips", "web_search"),
    ("Can you please search the weather tomorrow", "web_search"),
    ("remind me to call the bank", "reminders"),
    ("set a reminder for friday", "reminders"),
    ("email sam@example.com and say I will be late", "email"),
    ("Could you write an email to my professor", "email"),
    ("put the dentist on my calendar", "calendar"),
    ("schedule a meeting with Priya tomorrow", "calendar"),
    ("take a note: buy milk", "notes"),
    ("nova, jot this down: ideas", "notes"),
]
CONVERSATION = [
    "I have a meeting tomorrow that stresses me out",
    "my schedule is crazy",
    "that song reminded me of my dad",
    "I got an email from my professor and I'm worried",
    "remind me what happened with my exam",
    "I was searching for answers all night",
    "I need to write down my feelings",
    "note that I'm tired lol",
]


@pytest.mark.parametrize("message,tool", REQUESTS)
def test_requests_route_to_their_tool(message, tool):
    assert keyword_route(message)[0] == tool


@pytest.mark.parametrize("message", CONVERSATION)
def test_conversation_is_never_hijacked(message):
    assert keyword_route(message) is None
