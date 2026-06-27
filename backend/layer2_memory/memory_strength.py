"""Memory Strength decay model (architecture doc §8.3).

Every memory is a signal with strength that grows on reinforcement and decays over time.
Importance slows decay, so a life event outcompetes yesterday's small talk months later.
"""

from __future__ import annotations

import math

# Default base decay constant (§8.3). λ = base_decay × (1 − importance).
BASE_DECAY = 0.10

# Initial-strength weights: S0 = w1·base_importance + w2·emotional_weight + w3·novelty.
W_BASE = 0.5
W_EMOTION = 0.3
W_NOVELTY = 0.2

# Strength below this triggers deletion/archival (§8.3).
WEAK_THRESHOLD = 0.1
# Importance at/above this archives instead of deleting a weak memory.
ARCHIVE_IMPORTANCE = 0.5


def initial_strength(base_importance: float, emotional_weight: float, novelty: float) -> float:
    """S0 at creation: a weighted blend of importance, emotional weight, and novelty (§8.3)."""
    return W_BASE * base_importance + W_EMOTION * emotional_weight + W_NOVELTY * novelty


def decay_rate(importance: float, base_decay: float = BASE_DECAY) -> float:
    """λ = base_decay × (1 − importance). High-importance memories decay slowly (§8.3)."""
    return base_decay * (1.0 - importance)


def decayed_strength(S0: float, decay_rate: float, t_days: float) -> float:
    """S(t) = S0 · exp(−λ·t). Exponential decay over elapsed days (§8.3)."""
    return S0 * math.exp(-decay_rate * t_days)


def reinforce(S_old: float, reinforcement_signal: float) -> float:
    """S_new = S_old + log(1 + signal). Logarithmic returns prevent runaway growth (§8.3).

    ``reinforcement_signal`` ∈ [0, 1] reflects the strength of the recall context.
    """
    signal = max(0.0, min(1.0, reinforcement_signal))
    return S_old + math.log(1.0 + signal)


def deletion_decision(S_current: float, importance: float) -> str:
    """Decide a weak memory's fate (§8.3): 'delete', 'archive', or 'keep'.

    * S(t) < 0.1 and importance < 0.5 → delete
    * S(t) < 0.1 and importance ≥ 0.5 → archive (retrievable under strong cue)
    * otherwise → keep
    """
    if S_current < WEAK_THRESHOLD:
        return "delete" if importance < ARCHIVE_IMPORTANCE else "archive"
    return "keep"
