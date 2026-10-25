"""The Memory Arbiter — orchestration logic (architecture doc §11).

The single interface through which all other layers access Layer 2. It loads candidates,
runs the recall scoring engine + context gate, queries the User World Model, and returns a
read-only ``MemoryPacket``. No downstream agent calls a memory sub-component directly.

All failures degrade gracefully (§15): a packet is always returned, and an empty recall sets
the confabulation guard so the downstream prompt instructs Nova not to invent memories.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from . import competitive_recall, context_gate, recall_scorer
from .embedding import Embedder
from .recall_scorer import RecallWeights, DEFAULT_WEIGHTS
from .schemas import (
    ConversationMode,
    EmotionVector,
    EpisodicMemory,
    MemoryPacket,
    RecallResult,
    ScoredMemory,
    ShortTermMemoryBuffer,
    UWMContextSnapshot,
)

# Composite query weights: last message / session topic / due-thread summaries (§8.2).
QUERY_MESSAGE_WEIGHT = 0.6
QUERY_TOPIC_WEIGHT = 0.3
QUERY_THREAD_WEIGHT = 0.1


def build_query_embedding(
    embedder: Embedder,
    message: str,
    topic_summary: str = "",
    thread_summaries: Optional[list[str]] = None,
) -> list[float]:
    """Composite recall query embedding (§8.2): a weighted blend that prevents single-message
    over-fitting. Components are embedded, weighted, summed, and L2-normalized."""
    parts = [(message or "", QUERY_MESSAGE_WEIGHT), (topic_summary or "", QUERY_TOPIC_WEIGHT)]
    if thread_summaries:
        parts.append((" ".join(thread_summaries), QUERY_THREAD_WEIGHT))

    combined: list[float] = []
    for text, weight in parts:
        if not text.strip():
            continue
        vec = embedder.embed(text)
        if not combined:
            combined = [0.0] * len(vec)
        for i, x in enumerate(vec):
            combined[i] += weight * x

    if not combined:
        return embedder.embed(message or "")
    norm = math.sqrt(sum(x * x for x in combined))
    return [x / norm for x in combined] if norm else combined


# Mood-congruent bypass (§18.3): a distressed user may be reminded of a closely matching past
# distress even without topical overlap — but only on a near-exact emotional match.
_DISTRESS_VALENCE = -0.3
_EMOTIONAL_MATCH = 0.85


def _relevant(components: dict, current_emotion: EmotionVector, min_semantic: float) -> bool:
    """Three of the four recall signals are query-independent, so without a semantic floor the
    user's "most important" memories surface for any message, even "hey"."""
    if components["semantic"] >= min_semantic:
        return True
    return current_emotion.valence <= _DISTRESS_VALENCE and components["emotional"] >= _EMOTIONAL_MATCH


def _current_strength(memory) -> float:
    return getattr(memory, "S_current", 1.0)


async def memory_arbiter(
    user_id: UUID,
    query_text: str,
    current_emotion: EmotionVector,
    conversation_mode: ConversationMode,
    now: datetime,
    *,
    store,
    embedder: Embedder,
    stm: Optional[ShortTermMemoryBuffer] = None,
    session_topic_summary: str = "",
    due_thread_summaries: Optional[list[str]] = None,
    fuzzy_label_util=None,
    weights: RecallWeights = DEFAULT_WEIGHTS,
    active_narrative_chains: Optional[list] = None,
    min_semantic: float = 0.0,
) -> MemoryPacket:
    """Run the full recall pipeline and assemble the MemoryPacket (§11.2)."""

    packet = MemoryPacket(
        stm_turns=stm.turns[-10:] if stm else [],
        fuzzy_label_util=fuzzy_label_util,
        active_narrative_chains=active_narrative_chains or [],
    )

    # ── Candidate load (guarded — §15 vector-store-unavailable fallback) ──
    try:
        candidates = store.candidate_memories(user_id)
    except Exception:  # noqa: BLE001
        packet.recall_degraded = True
        packet.no_relevant_memories = True
        packet.confabulation_guard = True
        return packet

    if not candidates:
        packet.cold_start = True
        packet.no_relevant_memories = True
        packet.confabulation_guard = True
        _attach_uwm(packet, store, user_id, query_text)
        return packet

    # ── Score + gate every candidate ─────────────────────────────────────
    query_emb = build_query_embedding(
        embedder, query_text, session_topic_summary, due_thread_summaries
    )
    scored: list[ScoredMemory] = []
    for mem in candidates:
        recall_score, components = recall_scorer.score_memory(
            mem, query_emb, current_emotion, now, weights
        )
        if not _relevant(components, current_emotion, min_semantic):
            continue
        kind = context_gate.memory_gate_kind(mem)
        gate = context_gate.gate_value(conversation_mode, kind)
        s_current = _current_strength(mem)
        effective = competitive_recall.effective_score(recall_score, s_current, gate)
        label = ""
        if fuzzy_label_util and isinstance(mem, EpisodicMemory) and mem.created_at:
            label = fuzzy_label_util(mem.created_at)
        scored.append(ScoredMemory(
            memory=mem, recall_score=recall_score, effective_score=effective,
            gate_value=gate, components=components, fuzzy_temporal_label=label,
        ))

    selected = competitive_recall.select_recall(scored, cap=competitive_recall.MAX_RECALL)
    packet.recalled_memories = selected
    packet.retrieval_metadata = RecallResult(
        memories=selected,
        total_candidates_evaluated=len(candidates),
        retrieval_mode=conversation_mode.value,
        temperature_used=competitive_recall.temperature_for_mode(conversation_mode),
    )

    if not selected:
        packet.no_relevant_memories = True
        packet.confabulation_guard = True

    _attach_uwm(packet, store, user_id, query_text)
    return packet


def _attach_uwm(packet: MemoryPacket, store, user_id: UUID, query_text: str) -> None:
    """Populate the UWM context snapshot, flagging unavailability per §15."""
    try:
        uwm = store.load_uwm(user_id)
    except Exception:  # noqa: BLE001
        uwm = None
    if uwm is None:
        packet.uwm_unavailable = True
        return

    rel = store.query_uwm(user_id, "relationship_context", query_text)
    posture = store.query_uwm(user_id, "psychological_posture")
    packet.uwm_context = UWMContextSnapshot(
        user_profile_brief=uwm.profile.career_goals_summary or "",
        relevant_people=rel.get("relevant_people", []),
        active_stressors=uwm.life_context.active_stressors,
        active_situations=uwm.life_context.active_situations,
        psychological_posture=posture,
        communication_preferences=uwm.communication_model,
    )
