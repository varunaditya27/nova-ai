"""Upstream view-model records (read-only inputs) — Layer 10's read-only view of Layers 1/2/3.

Goals are duck-typed (any object with ``status``/``created_at``/``status_changed_at`` works, e.g.
Layer 7's Goal) so no Goal view-model type lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class EmotionalRecord:
    date: date
    valence: float = 0.0            # -1.0 .. 1.0
    arousal: float = 0.0            # 0.0 .. 1.0
    primary_emotion: str = "neutral"
    emotional_intensity: float = 0.0


@dataclass
class SessionRecord:
    session_id: str
    date: date
    duration_mins: float = 0.0
    user_message_length: float = 0.0
    self_disclosure_events: int = 0
    crisis_mode_active: bool = False


@dataclass
class EpisodicRecord:
    episode_id: str
    date: date
    importance_score: float = 0.0
    emotional_intensity: float = 0.0
    topics: list = field(default_factory=list)
    is_life_event_anchor: bool = False
    title: str = ""
