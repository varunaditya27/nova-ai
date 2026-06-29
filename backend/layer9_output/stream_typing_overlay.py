"""SC-1 — Stream Typing Overlay (architecture doc §3.2).

Intercepts Layer 4's token stream and emits typing events with a minimum inter-token delay,
smoothing variable generation speed into plausible typing. The delay is keyed to conversation
mode, modulated by circadian band, and given natural ±variability via an injected ``rng``
(``gauss``) so tests are deterministic. Sentence boundaries inject an additional pause.

This is client-side visual pacing, not added server latency: the full response is available;
the UI renders tokens with these delays.
"""

from __future__ import annotations

import random as _random

from backend.layer9_output.schemas import TypingEvent, TypingEventType


class StreamTypingOverlay:
    # Minimum delay between token emissions (ms) per conversation mode (architecture doc §3.2).
    MIN_TOKEN_DELAY_MS = {
        "casual_chat":       40,
        "task_help":         35,
        "emotional_support": 65,
        "crisis_support":    80,
        "deep_reasoning":    50,
        "technical":         35,
        "celebration":       45,
    }
    _DEFAULT_DELAY_MS = 45

    # Additional sentence-boundary pause (ms) at "." "?" "!" boundaries.
    SENTENCE_PAUSE_MS = {
        "casual_chat":       120,
        "emotional_support": 350,
        "crisis_support":    500,
        "deep_reasoning":    200,
        "technical":         100,
        "celebration":       80,
    }
    _DEFAULT_SENTENCE_PAUSE_MS = 150
    _FLOOR_MS = 20

    def compute_token_delay(self, conversation_mode: str, circadian_band: str, rng=_random) -> int:
        base = self.MIN_TOKEN_DELAY_MS.get(conversation_mode, self._DEFAULT_DELAY_MS)
        if circadian_band == "late_night":
            base = int(base * 1.30)
        elif circadian_band in ("morning", "early_morning"):
            base = int(base * 0.90)
        noise_factor = rng.gauss(1.0, 0.12)
        return max(self._FLOOR_MS, int(base * noise_factor))

    def emit_token(
        self, token: str, prev_token: str, conversation_mode: str,
        circadian_band: str, rng=_random,
    ) -> list[TypingEvent]:
        """Emit the event(s) for one token: an optional sentence pause then the token (doc §3.2)."""
        events: list[TypingEvent] = []
        delay = self.compute_token_delay(conversation_mode, circadian_band, rng)

        if (prev_token or "").rstrip() in (".", "?", "!"):
            pause = self.SENTENCE_PAUSE_MS.get(conversation_mode, self._DEFAULT_SENTENCE_PAUSE_MS)
            if circadian_band == "late_night":
                pause = int(pause * 1.25)
            events.append(TypingEvent(event_type=TypingEventType.PAUSE.value,
                                      delay_before_ms=pause))

        events.append(TypingEvent(event_type=TypingEventType.TOKEN.value,
                                  token=token, delay_before_ms=delay))
        return events
