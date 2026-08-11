"""SC-4 ProactiveContext + delivery + validation (architecture doc §6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import DeliveryChannel


@dataclass
class ProactiveContext:
    source_memory_summaries: list[str] = field(default_factory=list)
    source_thread_summary: Optional[str] = None
    source_event_summary: Optional[str] = None
    source_goal_summary: Optional[str] = None

    user_name_if_known: Optional[str] = None
    current_life_context: str = ""
    bes_trend_description: str = ""

    persona_instruction: str = ""
    relationship_stage: str = "developing"
    voice_parameters_summary: str = ""
    prior_proactive_topics: list[str] = field(default_factory=list)


@dataclass
class ProactiveValidationResult:
    passed: bool = True
    issue: Optional[str] = None
    action: Optional[str] = None


@dataclass
class ProactiveDeliveryPayload:
    user_id: str = ""
    message_text: str = ""
    item_id: str = ""
    delivery_channel: str = DeliveryChannel.PUSH_NOTIFICATION.value
    delivery_channel_priority: list[str] = field(default_factory=list)
    send_at: Optional[datetime] = None
    expiry_after_send: int = 0
    allow_reply: bool = True
    tracking_enabled: bool = True
