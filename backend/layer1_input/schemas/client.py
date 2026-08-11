"""Service interface payload types (architecture doc §12.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from .enums import AttachmentType


@dataclass
class AttachmentPayload:
    """A single non-text attachment accompanying a message.

    ``data`` holds raw bytes in RAM only — never persisted (§6.4 privacy constraint).
    """

    attachment_type: AttachmentType
    mime_type: Optional[str] = None
    data: Optional[bytes] = None
    filename: Optional[str] = None
    size_bytes: Optional[int] = None
    # Location attachments only:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_name: Optional[str] = None
    # Reaction attachments only:
    reaction_emoji: Optional[str] = None


@dataclass
class ClientMetadata:
    """Behavioral metadata the client app reports alongside every message (§12.2).

    The two ``*_proactive`` fields extend the original spec so SC-2 can resolve
    ``initiation_type`` without reaching into Layer 6 (see architecture doc §4.5 — the
    server cannot derive whether the previous Nova turn was a proactive reach-out).
    """

    session_id: UUID
    nova_last_delivered_at: Optional[datetime] = None
    user_typing_started_at: Optional[datetime] = None
    deletion_occurred: bool = False
    deletion_count: int = 0
    peak_draft_length_chars: int = 0
    final_draft_length_chars: int = 0
    is_burst: bool = False
    burst_count: int = 1
    burst_messages: Optional[list[str]] = None
    last_nova_message_was_proactive: bool = False
    is_reply_to_proactive: bool = False
