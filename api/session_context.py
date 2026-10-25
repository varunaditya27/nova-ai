"""Layer-2 prompt-side readers for in-session turns (STM) and ongoing narrative arcs.

Both were written every turn and never read back: ``stm.turns`` (docs/layer-2-architecture.md
SC-1) and ``active_narrative_chains`` (SC-8). This turns them into one plain-language planner
directive — no timestamps or scores, per the fuzzy-temporal / no-raw-numbers invariants.
"""
from __future__ import annotations

_RECENT_TURNS = 6
_TURN_CHARS = 200
_MAX_CHAINS = 2


def make_session_context_provider(stm_store, memory_store):
    def _provider(user_id, session_id) -> str:
        parts = []
        stm = stm_store.get(session_id or "default")
        if stm is not None and stm.turns:
            lines = [f"{'They' if t.role == 'user' else 'You'}: {t.content[:_TURN_CHARS]}"
                     for t in stm.turns[-_RECENT_TURNS:]]
            parts.append("Earlier in this same conversation (for continuity only — don't repeat "
                         "it back): " + " | ".join(lines))
        chains = [c for c in memory_store.active_narrative_chains(user_id)
                  if c.theme and len(c.episodes) > 1]
        chains.sort(key=lambda c: c.last_episode_at or c.first_episode_at, reverse=True)
        if chains:
            themes = "; ".join(c.arc_summary or c.theme for c in chains[:_MAX_CHAINS])
            parts.append("Ongoing storylines in their life you may build on if relevant "
                         f"(never announce them): {themes}.")
        return " ".join(parts)
    return _provider
