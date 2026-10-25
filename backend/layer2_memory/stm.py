"""SC-1 · Short-Term Memory buffer (architecture doc §3).

The raw conversational buffer for the current session — a sliding window providing in-session
coherence. Ephemeral (RAM only, never persisted). When it overflows, the oldest turns are
evicted; each evicted turn is checked for promotion to episodic memory before discard.
"""

from __future__ import annotations

import re

from .schemas import ConversationTurn, ShortTermMemoryBuffer

# High-arousal turns are promoted to episodic memory (§3.3).
PROMOTION_AROUSAL_THRESHOLD = 0.6

# Life-event signal keywords that force promotion of an evicted turn (§3.3).
LIFE_EVENT_KEYWORDS = (
    "got the job", "new job", "passed away", "broke up", "diagnosed", "moving out",
    "graduated", "engaged", "got married", "fired", "promotion", "promoted",
    "accepted", "rejected", "offer", "interview",
)


# A calm, substantive statement *about the user's own life* ("I'm vegetarian and live in Pune",
# "my sister Meera visits next week") is exactly what a long-term companion must remember, yet it
# trips neither arousal nor a life-event keyword. Questions and short chatter are not disclosures.
_MIN_DISCLOSURE_WORDS = 8
_DISCLOSURE = re.compile(
    r"\b(i am|i'm|i have|i've|i got|i work|i live|i study|i love|i hate|i prefer|i usually|"
    r"i always|i never|my (?:\w+ )?(?:is|are|was|name|mom|mum|dad|sister|brother|friend|job|boss|"
    r"partner|family|wife|husband|roommate))\b", re.IGNORECASE)


def is_personal_disclosure(content: str) -> bool:
    text = content.strip()
    return (len(text.split()) >= _MIN_DISCLOSURE_WORDS and not text.endswith("?")
            and _DISCLOSURE.search(text) is not None)


def add_turn(buffer: ShortTermMemoryBuffer, turn: ConversationTurn) -> list[ConversationTurn]:
    """Append a turn and evict the oldest turns past the size/char limits (§3.3).

    Returns the list of evicted turns (oldest first) so the State Updater can run the
    promotion check before they are discarded.
    """
    buffer.turns.append(turn)
    buffer.total_chars += len(turn.content)

    evicted: list[ConversationTurn] = []
    while buffer.turns and (
        len(buffer.turns) > buffer.max_turns or buffer.total_chars > buffer.char_limit
    ):
        oldest = buffer.turns.pop(0)
        buffer.total_chars -= len(oldest.content)
        evicted.append(oldest)
    return evicted


def should_promote(turn: ConversationTurn) -> bool:
    """Decide whether an evicted turn should become an episodic memory (§3.3)."""
    if turn.importance_flag:
        return True
    if turn.emotional_annotation and turn.emotional_annotation.arousal > PROMOTION_AROUSAL_THRESHOLD:
        return True
    content = turn.content.lower()
    if any(keyword in content for keyword in LIFE_EVENT_KEYWORDS):
        return True
    return is_personal_disclosure(turn.content)
