"""Layer 2 — Cognition & Memory.

The cognitive core of NovaAI. Memory is not storage — it is a dynamic signal with strength,
decay, emotional resonance, and competitive selection (architecture doc §1).

Eight sub-components across three groups:
  * Storage — Short-Term buffer (``stm``), Episodic / Semantic / Identity stores and the
    User World Model (``memory_store``, ``semantic_memory``, ``identity``)
  * Processing — recall scoring (``recall_scorer``), context gate (``context_gate``),
    competitive recall (``competitive_recall``), the Forgetting & Consolidation Engine
    (``forgetting_engine``), and the memory-strength model (``memory_strength``)
  * State — the Memory Audit Trail + narrative linking (``audit_trail``)

The ``arbiter`` is the single read interface (returns a ``MemoryPacket``); the
``state_updater`` is the single write path (runs after the turn). Embeddings/index live in
``embedding``; the full contract is in ``schemas`` and ``docs/layer-2-architecture.md``.
"""

from .arbiter import build_query_embedding, memory_arbiter
from .audit_trail import AuditTrail, detect_narrative_links
from .competitive_recall import effective_score, select_recall, softmax, temperature_for_mode
from .context_gate import gate_value, memory_gate_kind
from .embedding import (
    BruteForceVectorIndex,
    DeterministicEmbedder,
    Embedder,
    VectorIndex,
    cosine_similarity,
)
from .forgetting_engine import (
    cluster_detection,
    decay_sweep,
    extract_semantic_memory,
    should_trigger_fce,
)
from .identity import apply_identity_update, update_threshold
from .memory_store import InMemoryMemoryStore, resolve_uwm_query
from .memory_strength import (
    decay_rate,
    decayed_strength,
    deletion_decision,
    initial_strength,
    reinforce,
)
from .recall_scorer import DEFAULT_WEIGHTS, RecallWeights, score_memory
from .schemas import (
    ConversationMode,
    EmotionVector,
    EpisodicMemory,
    IdentityMemory,
    MemoryPacket,
    ScoredMemory,
    SemanticMemory,
    ShortTermMemoryBuffer,
    UserWorldModel,
)
from .semantic_memory import handle_contradiction
from .state_updater import StateUpdateResult, state_updater
from .stm import add_turn, should_promote

__all__ = [
    # Orchestration
    "memory_arbiter",
    "state_updater",
    "StateUpdateResult",
    "build_query_embedding",
    # Stores
    "InMemoryMemoryStore",
    # Recall
    "score_memory",
    "RecallWeights",
    "DEFAULT_WEIGHTS",
    "gate_value",
    "memory_gate_kind",
    "softmax",
    "effective_score",
    "select_recall",
    "temperature_for_mode",
    # FCE
    "should_trigger_fce",
    "decay_sweep",
    "cluster_detection",
    "extract_semantic_memory",
    # Strength
    "initial_strength",
    "decay_rate",
    "decayed_strength",
    "reinforce",
    "deletion_decision",
    # Semantic / identity
    "handle_contradiction",
    "apply_identity_update",
    "update_threshold",
    # STM
    "add_turn",
    "should_promote",
    # Audit
    "AuditTrail",
    "detect_narrative_links",
    # Embedding
    "cosine_similarity",
    "DeterministicEmbedder",
    "Embedder",
    "BruteForceVectorIndex",
    "VectorIndex",
    # Schemas
    "MemoryPacket",
    "EpisodicMemory",
    "SemanticMemory",
    "IdentityMemory",
    "ShortTermMemoryBuffer",
    "UserWorldModel",
    "ScoredMemory",
    "EmotionVector",
    "ConversationMode",
]
