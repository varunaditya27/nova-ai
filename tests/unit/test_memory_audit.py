"""Tests for SC-8 Audit Trail hash chain + cross-session narrative linking (architecture doc §10)."""

from datetime import datetime, timedelta
from uuid import uuid4

from backend.layer2_memory import audit_trail as at
from backend.layer2_memory.embedding import DeterministicEmbedder
from backend.layer2_memory.schemas import (
    AuditEvent,
    AuditEventType,
    ChainedEpisode,
    EpisodicMemory,
    NarrativeChain,
    NarrativeLinkType,
)

NOW = datetime(2026, 6, 26)
EMB = DeterministicEmbedder(dim=64)


# ── Hash chain integrity (§10.2) ─────────────────────────────────────────────
def test_append_builds_valid_hash_chain():
    trail = at.AuditTrail()
    for i in range(5):
        trail.append(AuditEvent(event_type=AuditEventType.MEMORY_CREATED, reason=f"e{i}",
                                timestamp=NOW))
    assert trail.verify() is True
    assert len(trail.events) == 5


def test_first_event_links_to_genesis():
    trail = at.AuditTrail()
    trail.append(AuditEvent(event_type=AuditEventType.MEMORY_CREATED, reason="first", timestamp=NOW))
    assert trail.events[0].prev_event_hash == at.GENESIS_HASH


def test_chain_links_sequential_hashes():
    trail = at.AuditTrail()
    trail.append(AuditEvent(reason="a", timestamp=NOW))
    trail.append(AuditEvent(reason="b", timestamp=NOW))
    assert trail.events[1].prev_event_hash == trail.events[0].content_hash


def test_tampering_is_detected():
    trail = at.AuditTrail()
    for i in range(3):
        trail.append(AuditEvent(reason=f"e{i}", timestamp=NOW))
    trail.events[1].reason = "tampered"  # mutate a past event without rehashing
    assert trail.verify() is False


# ── Cross-session narrative linking (§10.3) ──────────────────────────────────
def _ep(text, entities, **kw):
    return EpisodicMemory(summary=text, embedding=EMB.embed(text), entity_refs=entities,
                          created_at=NOW, **kw)


def test_narrative_link_detected_for_continuation():
    seed = _ep("placement interview prep with Rohan", ["Rohan"])
    chain = NarrativeChain(
        theme="placements", first_episode_at=NOW,
        episodes=[ChainedEpisode(episode_id=seed.memory_id, position_in_chain=0)],
    )
    new_ep = _ep("placement interview prep with Rohan again", ["Rohan"])
    matched = at.detect_narrative_links(new_ep, [chain], {seed.memory_id: seed}, now=NOW)
    assert matched is chain
    assert len(chain.episodes) == 2
    assert chain.episodes[1].episode_id == new_ep.memory_id


def test_no_link_when_dissimilar():
    seed = _ep("placement interview prep", ["Rohan"])
    chain = NarrativeChain(
        episodes=[ChainedEpisode(episode_id=seed.memory_id, position_in_chain=0)])
    unrelated = _ep("trying a new pasta recipe", ["Mom"])
    matched = at.detect_narrative_links(unrelated, [chain], {seed.memory_id: seed}, now=NOW)
    assert matched is None
    assert len(chain.episodes) == 1


def test_resolution_link_marks_chain_resolved():
    seed = _ep("placement interview prep with Rohan", ["Rohan"])
    chain = NarrativeChain(
        episodes=[ChainedEpisode(episode_id=seed.memory_id, position_in_chain=0)])
    new_ep = _ep("placement interview prep with Rohan resolved", ["Rohan"])
    at.detect_narrative_links(
        new_ep, [chain], {seed.memory_id: seed}, now=NOW,
        classify_fn=lambda a, b: NarrativeLinkType.RESOLUTION,
    )
    assert chain.status.value == "resolved"


def test_resolved_chains_are_skipped():
    from backend.layer2_memory.schemas import ChainStatus
    seed = _ep("placement interview prep with Rohan", ["Rohan"])
    chain = NarrativeChain(
        status=ChainStatus.RESOLVED,
        episodes=[ChainedEpisode(episode_id=seed.memory_id, position_in_chain=0)])
    new_ep = _ep("placement interview prep with Rohan", ["Rohan"])
    assert at.detect_narrative_links(new_ep, [chain], {seed.memory_id: seed}, now=NOW) is None
