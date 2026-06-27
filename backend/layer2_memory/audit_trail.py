"""SC-8 · Memory Audit Trail + cross-session narrative linking (architecture doc §10).

The complete, tamper-evident log of every memory lifecycle event (SHA-256 hash chain), plus
the narrative link graph that connects episodes into arcs across sessions. The audit trail is
the trust foundation: the user can always see why a memory exists, was recalled, or was deleted.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable, Optional
from uuid import UUID

from .embedding import cosine_similarity
from .schemas import (
    AuditEvent,
    ChainedEpisode,
    ChainStatus,
    EpisodicMemory,
    NarrativeChain,
    NarrativeLinkType,
)

# Hash that precedes the first event in a chain.
GENESIS_HASH = "0" * 64

# Narrative link detection (§10.3).
LINK_SCORE_THRESHOLD = 0.65
SEMANTIC_LINK_WEIGHT = 0.6
ENTITY_LINK_WEIGHT = 0.4

# (new_episode, last_episode) → link type. Production wires an LLM/heuristic; default is
# continuation.
LinkClassifier = Callable[[EpisodicMemory, EpisodicMemory], NarrativeLinkType]


def _compute_hash(event: AuditEvent) -> str:
    """SHA-256 over the event's content + the previous event's hash (chain integrity)."""
    payload = "|".join(
        [
            str(event.event_type.value if hasattr(event.event_type, "value") else event.event_type),
            str(event.memory_id),
            str(event.session_id),
            str(event.timestamp),
            event.reason,
            str(event.score_at_event),
            str(event.prior_value),
            str(event.new_value),
            event.triggered_by,
            event.prev_event_hash,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditTrail:
    """Append-only, tamper-evident event log (§10.2)."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        event.prev_event_hash = self.events[-1].content_hash if self.events else GENESIS_HASH
        event.content_hash = _compute_hash(event)
        self.events.append(event)
        return event

    def verify(self) -> bool:
        """Recompute the chain; any past-event mutation invalidates subsequent hashes (§10.2)."""
        prev = GENESIS_HASH
        for event in self.events:
            if event.prev_event_hash != prev:
                return False
            if event.content_hash != _compute_hash(event):
                return False
            prev = event.content_hash
        return True


def _default_classifier(new_ep: EpisodicMemory, last_ep: EpisodicMemory) -> NarrativeLinkType:
    return NarrativeLinkType.CONTINUATION


def detect_narrative_links(
    new_episode: EpisodicMemory,
    existing_chains: list[NarrativeChain],
    episodes_by_id: dict[UUID, EpisodicMemory],
    now: datetime,
    classify_fn: LinkClassifier = _default_classifier,
) -> Optional[NarrativeChain]:
    """Attach a new episode to an existing narrative chain if it continues one (§10.3).

    ``link_score = 0.6·semantic_similarity + 0.4·entity_overlap``. Resolved/archived chains are
    skipped. Returns the matched chain (mutated in place) or ``None`` to seed a new chain.
    """
    for chain in existing_chains:
        if chain.status in (ChainStatus.RESOLVED, ChainStatus.ARCHIVED):
            continue
        if not chain.episodes:
            continue

        last = episodes_by_id.get(chain.episodes[-1].episode_id)
        if last is None:
            continue

        semantic = cosine_similarity(new_episode.embedding, last.embedding)
        shared = set(new_episode.entity_refs) & set(last.entity_refs)
        entity_overlap = len(shared) / max(len(new_episode.entity_refs), 1)
        link_score = SEMANTIC_LINK_WEIGHT * semantic + ENTITY_LINK_WEIGHT * entity_overlap

        if link_score > LINK_SCORE_THRESHOLD:
            link_type = classify_fn(new_episode, last)
            chain.episodes.append(
                ChainedEpisode(
                    episode_id=new_episode.memory_id,
                    position_in_chain=len(chain.episodes),
                    link_type=link_type,
                    linked_at=now,
                )
            )
            chain.last_episode_at = new_episode.created_at
            if link_type == NarrativeLinkType.RESOLUTION:
                chain.status = ChainStatus.RESOLVED
            return chain

    return None
