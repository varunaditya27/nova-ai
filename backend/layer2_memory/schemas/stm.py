"""SC-1 Short-Term Memory Buffer types (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from .emotion import EmotionVector


@dataclass
class ConversationTurn:
    turn_id: UUID = field(default_factory=uuid4)
    role: Literal["user", "assistant"] = "user"
    content: str = ""
    timestamp: Optional[datetime] = None
    word_count: int = 0
    emotional_annotation: Optional[EmotionVector] = None
    intent_label: Optional[str] = None
    importance_flag: bool = False


@dataclass
class ShortTermMemoryBuffer:
    session_id: UUID
    user_id: UUID
    turns: list[ConversationTurn] = field(default_factory=list)
    max_turns: int = 100
    total_chars: int = 0
    char_limit: int = 30000
