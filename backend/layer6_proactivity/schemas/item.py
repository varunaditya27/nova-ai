"""SC-1 ProactiveItem (architecture doc §3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .enums import ItemStatus, ProactiveItemType


@dataclass
class ProactiveItem:
    item_id: str = field(default_factory=lambda: str(uuid4()))
    item_type: str = ProactiveItemType.THREAD_FOLLOW_UP.value
    source_layer: str = "layer1"

    # Content basis
    content_basis: str = ""
    content_basis_valence: Optional[float] = None
    source_memory_ids: list[str] = field(default_factory=list)
    source_event_ids: list[str] = field(default_factory=list)
    source_goal_id: Optional[str] = None

    # SC-4 generated delivery text (§6, 2026-08-09) — the real, natural-language message a user
    # would actually see, as opposed to content_basis (an internal fragment like "Goal: X |
    # Milestone: Y"). Populated by background/proactive_check_job.py once an item clears the
    # timing gate; empty until then.
    generated_message: str = ""

    # People involved
    person_id: Optional[str] = None
    person_display_name: Optional[str] = None

    # Priority
    base_priority: float = 0.5
    current_priority: float = 0.5
    priority_last_updated: Optional[datetime] = None

    # Timing
    earliest_send_time: Optional[datetime] = None
    optimal_send_window: Optional[tuple] = None    # (start, end)
    expiry_time: Optional[datetime] = None

    # Lifecycle
    status: str = ItemStatus.PENDING.value
    created_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    send_attempt_count: int = 0

    # Response tracking
    user_response_valence: Optional[float] = None
    user_engaged: Optional[bool] = None
