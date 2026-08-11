"""SC-1 Progressive Elicitation schemas (architecture doc §4.2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

ELICITATION_CATEGORIES = (
    "identity", "life_context", "communication_pref", "goals",
    "relationships", "values", "emotional_style", "reason_for_use",
)


@dataclass
class ElicitationItem:
    category: str
    inference_target: str
    priority: int                                  # 1=critical, 2=important, 3=nice-to-have
    question: Optional[str] = None                 # None => inferred-only, never asked
    prerequisite_item_ids: list = field(default_factory=list)
    can_infer_without_asking: bool = False
    natural_triggers: list = field(default_factory=list)
    status: str = "waiting"                         # waiting|surfaced|answered|inferred|expired
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    surfaced_at_session: Optional[int] = None
    answered_at_session: Optional[int] = None
