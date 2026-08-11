# Layer 2 — Cognition & Memory
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

If Layer 1 answers *when*, Layer 2 answers *what Nova knows, how it knows it, and how it decides what to recall*. This is the cognitive core of the entire NovaAI architecture. Every other layer is downstream of this one working correctly. Remove it and you have a sophisticated prompt engine. Keep it and you have something that accumulates — that gets qualitatively richer across time.

The central thesis is this:

> **Memory is not storage. It is a dynamic signal with strength, decay, emotional resonance, and competitive selection.**

Getting this right is what makes Nova feel like it *knows* you. Getting it wrong produces the uncanny valley of the AI that remembers your name but not what it means.

Layer 2 contains **eight sub-components** organized into three functional groups:

- **Storage Group**: the five memory types and their schemas
- **Processing Group**: the scoring function, competitive recall, context gating, and the Forgetting & Consolidation Engine
- **State Group**: the User World Model, cross-session narrative linking, and the Memory Audit Trail

All eight are fully specified here. There are no stubs, no deferred schemas.

---

## 2. Architecture Overview

```
Session begins
      │
      ▼
┌──────────────────────────────────────────┐
│  MEMORY ARBITER                          │
│  (orchestrates all sub-components below) │
└──────────────────────────────────────────┘
      │
      ├──► SC-1: Short-Term Buffer       (in-session only)
      │
      ├──► SC-2: Episodic Memory Store   (past events, summaries)
      │
      ├──► SC-3: Semantic Memory Store   (stable facts, preferences)
      │
      ├──► SC-4: Identity Memory Store   (Nova's self-model)
      │
      ├──► SC-5: User World Model        (structured user representation)
      │
      ├──► SC-6: Recall Scoring Engine   (four-component competitive retrieval)
      │
      ├──► SC-7: Forgetting & Consolidation Engine  (periodic maintenance)
      │
      └──► SC-8: Memory Audit Trail      (why every recall/deletion happened)

↓
MemoryPacket (read-only, passed to all downstream layers)

↓
Session ends →  State Updater runs:
                - Writes new episodic memories
                - Updates User World Model
                - Updates cross-session narrative links
                - Logs audit trail entries
                - Schedules next consolidation batch
```

The **Memory Arbiter** is the single entry point. No downstream agent queries a memory store directly. All reads go through the Arbiter; all writes go through the State Updater (which runs at session end, not during inference).

---

## 3. Sub-Component 1 — Short-Term Memory Buffer

### 3.1 Purpose

Short-Term Memory (STM) is the raw conversational buffer for the current session. It provides in-session coherence — the ability to refer back to what was said 3 messages ago without querying long-term storage. It is ephemeral by design.

### 3.2 Schema

```python
class ShortTermMemoryBuffer:
    session_id: UUID
    user_id: UUID
    turns: list[ConversationTurn]         # ordered; oldest first
    max_turns: int = 100                  # rolling window; oldest evicted when full (raised
                                           # from the original 40 once promotion-only extraction
                                           # went live, so ordinary conversation has room to
                                           # breathe before anything is evicted — see §19)
    total_chars: int                      # running character count
    char_limit: int = 30000               # approximate context window budget (raised from
                                           # the original 12,000 alongside max_turns — see §19)

class ConversationTurn:
    turn_id: UUID
    role: Literal["user", "assistant"]
    content: str                          # raw text of the message
    timestamp: datetime
    word_count: int
    emotional_annotation: Optional[EmotionVector]  # attached by Layer 3 during processing
    intent_label: Optional[str]           # attached by Layer 3: "venting", "question", etc.
    importance_flag: bool                 # set True if this turn spawned an episodic memory
```

### 3.3 Eviction Policy

The STM buffer operates as a sliding window. When `total_chars` exceeds `char_limit` or `turns` exceeds `max_turns`, the oldest turns are evicted. Eviction is not immediate deletion — before a turn is evicted, it is passed to the **Episodic Memory Extractor** (within the State Updater) for a promotion decision.

**Promotion criteria for evicted turns:**
- `importance_flag == True` — always promote
- `emotional_annotation.arousal > 0.6` — promote (high emotional intensity)
- Turn contains a life event signal keyword — promote
- Otherwise — discard without promotion

### 3.4 Persistence

STM lives **entirely in RAM** during the session. It is never written to disk in raw form. At session end, the State Updater processes the full buffer for episodic memory extraction, then the buffer is freed. No plaintext conversation transcripts are ever persisted.

---

## 4. Sub-Component 2 — Episodic Memory Store

### 4.1 Purpose

Episodic Memory is the heart of perceived humanness. These are structured summaries of meaningful past interactions. Not transcripts — summaries. An episode captures the *meaning* of a moment, not its verbatim record. This is what makes *"hey, how did that interview go?"* possible three weeks later.

### 4.2 Full Schema

```python
class EpisodicMemory:
    # Identity
    memory_id: UUID
    user_id: UUID
    session_id: UUID                      # session it was created in

    # Content
    summary: str                          # 1–3 sentence human-readable summary
    embedding: list[float]                # vector representation (384-dim, all-MiniLM-L6-v2)
    topic_tags: list[str]                 # e.g. ["academics", "anxiety", "placement"]
    entity_refs: list[str]                # people, places, orgs mentioned: ["Rohan", "IIT"]
    thread_id: Optional[UUID]             # links to NarrativeThread in Layer 1 if one was spawned

    # Temporal
    created_at: datetime
    session_timestamp: datetime           # when the original session occurred
    fuzzy_label: str                      # auto-computed: "a few weeks ago", "last month"

    # Emotional
    emotion_vector: EmotionVector         # emotional state at creation time
    emotional_weight: float               # 0–1; sqrt(valence² + arousal²)

    # Memory Strength
    importance_score: float               # 0–1; see importance classification table
    base_importance: float                # category-based initial score
    novelty_score: float                  # 0–1; how different this was from existing memories
    S0: float                             # initial strength at creation
    S_current: float                      # current decayed strength
    decay_rate: float                     # λ = base_decay × (1 – importance)
    last_decay_computed_at: datetime
    reinforcement_count: int              # how many times this memory was re-triggered
    is_archived: bool                     # True if S_current < 0.1 but importance ≥ 0.5

    # Lineage
    source_turn_ids: list[UUID]           # which STM turns generated this episode
    consolidated_into: Optional[UUID]     # if this episode was absorbed into a semantic memory
    linked_episodes: list[UUID]           # cross-session narrative links (see SC-8)
    superseded_by: Optional[UUID]         # if a later episode corrects/updates this one

    # Audit
    recall_history: list[RecallEvent]     # every time this memory was retrieved
    creation_agent: str                   # which process created it (State Updater, etc.)

class EmotionVector:
    valence: float        # –1 to +1 (negative to positive)
    arousal: float        # 0 to 1 (calm to activated)
    dominant_label: str   # "anxious", "joyful", "flat", "frustrated", "content", etc.

class RecallEvent:
    recalled_at: datetime
    trigger_query: str    # what query surfaced this memory
    score_at_recall: float
    context_mode: str     # "emotional_support", "casual", "technical"
    was_used_in_response: bool
```

### 4.3 Importance Classification Table

Base importance is assigned at creation time by the Episodic Memory Extractor based on content type:

| Category | Base Importance | Examples |
|---|---|---|
| `life_event_major` | 0.95 | Job offer, relationship change, family death, diagnosis |
| `life_event_minor` | 0.80 | Exam result, trip, starting a new habit |
| `emotional_peak` | 0.75 | Breakdown, confession, significant celebration |
| `goal_stated` | 0.70 | User explicitly states an intention or commitment |
| `conflict_interpersonal` | 0.72 | Conflict with a person in their life |
| `insight_expressed` | 0.65 | User has a realisation or expresses a new belief |
| `recurring_struggle` | 0.68 | Pattern of anxiety, self-doubt, recurring complaint |
| `relationship_update` | 0.60 | Update on someone in User World Model |
| `preference_revealed` | 0.45 | Stated like/dislike; minor personality signal |
| `factual_disclosure` | 0.40 | Neutral facts about life: major, schedule, etc. |
| `casual_exchange` | 0.15 | Small talk, jokes, day-to-day chatter |
| `task_request` | 0.10 | One-off requests with no relational significance |

### 4.4 Storage Backend

> **⚠ As-built (2026-07-04, authoritative):** the production **vector store is ChromaDB**
> (`infra/vector_store/`), running as its own service/container, with embeddings from the Ollama
> `nomic-embed-text` embedding function (cosine; collections `episodic`/`semantic`/`identity`). This
> **supersedes the hnswlib design described below** and the earlier pgvector mention. Relational
> state lives in PostgreSQL (`infra/db/`). The hnswlib text is retained as historical design
> rationale. See `docs/superpowers/specs/2026-07-04-infra-runtime-substrate-design.md`.

- **Vector store** *(historical design; superseded by ChromaDB — see note above)*: hnswlib — in-process, on-device, no server/network; `memory.vdb`; 384-dim all-MiniLM-L6-v2; cosine space, `ef_construction=200`, `M=16`
- **Metadata store**: SQLite (all non-vector fields), with B-tree indexes on `user_id`, `created_at`, `importance_score`
- **Encryption**: SQLCipher (on-device, encrypted at rest)

> **Implementation note:** the engine talks to the index through a `VectorIndex` protocol, so a
> dependency-free brute-force cosine index drives tests/offline dev; **ChromaDB** (`infra/vector_store/`)
> is the production implementation behind that protocol.

All episodic memories are stored on-device by default. Cloud sync is opt-in and requires explicit user consent (governed by Layer 12).

---

## 5. Sub-Component 3 — Semantic Memory Store

### 5.1 Purpose

Semantic Memory holds stable, generalized knowledge about the user — facts and patterns distilled from multiple episodic memories converging. These are not entered manually. They emerge automatically through the Forgetting & Consolidation Engine (SC-7). A semantic memory entry represents something Nova has *learned* about the user through repeated evidence.

### 5.2 Full Schema

```python
class SemanticMemory:
    # Identity
    memory_id: UUID
    user_id: UUID
    memory_type: Literal[
        "preference",           # stable like/dislike
        "communication_style",  # how user communicates
        "emotional_pattern",    # recurring emotional tendency
        "behavioral_tendency",  # how user typically acts
        "factual_stable",       # stable life fact: major, city, name
        "relationship_model",   # generalized pattern about a person in user's life
        "worldview",            # user's stated beliefs, values, or stances
        "trigger_pattern",      # things that reliably upset or energize the user
        "coping_mechanism"      # how user typically handles stress or conflict
    ]

    # Content
    statement: str              # "User gets defensive when technical decisions are questioned"
    embedding: list[float]      # vector for semantic search
    confidence: float           # 0–1; increases with each supporting episode
    supporting_episode_ids: list[UUID]   # which episodes generated this fact
    evidence_count: int         # number of distinct episodes confirming this

    # Temporal
    created_at: datetime
    last_confirmed_at: datetime # last time a new episode supported this fact
    last_contradicted_at: Optional[datetime]
    contradiction_count: int    # times contradicting evidence was received

    # Strength
    decay_rate: float           # very low; semantic memories are stable by design
    S_current: float            # still decays slowly if never reinforced
    is_deprecated: bool         # True if contradicted and evidence threshold crossed

    # Retrieval
    retrieval_tags: list[str]   # used by context gating to filter by topic area
    relevance_contexts: list[str]  # when is this fact useful: ["conflict", "advice", "planning"]
```

### 5.3 Contradiction Handling

When new episodic evidence contradicts an existing semantic memory, the following logic applies:

```python
def handle_contradiction(semantic: SemanticMemory, new_evidence: EpisodicMemory):
    semantic.contradiction_count += 1

    # Compute contradiction weight based on evidence strength
    evidence_strength = new_evidence.importance_score * new_evidence.S_current

    # Simple threshold: contradictions must accumulate to force deprecation
    # Required contradictions scale with confidence (high-confidence facts are harder to overturn)
    required_contradictions = math.ceil(2 + semantic.confidence * 6)
    # confidence 0.3 → ceil(3.8) = 4 contradictions
    # confidence 0.9 → ceil(7.4) = 8 contradictions
    # (The formula is authoritative; an earlier comment said "0.3 → 3", which was off by one.)

    if semantic.contradiction_count >= required_contradictions:
        semantic.is_deprecated = True
        # Do not delete — log as deprecated; audit trail records full evidence history
    else:
        # Reduce confidence proportionally
        semantic.confidence -= (evidence_strength * 0.15)
        semantic.confidence = max(semantic.confidence, 0.1)
        semantic.last_contradicted_at = datetime.utcnow()
```

Deprecated semantic memories are retained in the store with `is_deprecated = True`. They do not surface in normal retrieval but are accessible via the Memory Audit Tool (Layer 12) and inform the audit trail. This allows the system to reason about belief change over time.

---

## 6. Sub-Component 4 — Identity Memory Store

### 6.1 Purpose

Identity Memory is Nova's self-model. It stores Nova's beliefs, values, stances, behavioral anchors, and personality traits. These are what make Nova *consistent* — the same character across every conversation, with every user, on every topic. Without this sub-component, a single conversation can rewrite Nova's personality. With it, Nova's core identity is mathematically stable.

### 6.2 Full Schema

```python
class IdentityMemory:
    belief_id: UUID
    category: Literal[
        "core_value",           # fundamental ethical stance; hardest to change
        "personality_trait",    # warmth, curiosity, directness, humor style
        "opinion",              # stance on specific topics; updatable
        "behavioral_policy",    # how Nova acts in specific situations
        "self_knowledge",       # awareness of own limitations, capabilities
        "relational_stance",    # how Nova approaches relationships generally
        "aesthetic_preference"  # what kinds of expression Nova gravitates toward
    ]
    statement: str              # "Nova does not give medical diagnoses"
    centrality: float           # 0–1; how central to identity (core_value ≥ 0.8)
    update_threshold: float     # computed from centrality; see formula below
    evidence_for: list[str]     # episodes that support this belief
    evidence_against: list[str] # episodes that contradict it
    last_updated: datetime
    update_history: list[BeliefUpdateEvent]
    is_immutable: bool          # True for safety-critical policies (never changes)

class BeliefUpdateEvent:
    updated_at: datetime
    prior_statement: str
    new_statement: str
    triggering_session_id: UUID
    evidence_strength: float
    update_reason: str
```

### 6.3 Update Threshold Formula

The threshold for updating an identity belief scales with centrality:

```
threshold(centrality) = 0.5 × (1 + centrality²)
```

| Centrality | Update Threshold | What it means |
|---|---|---|
| 0.2 (peripheral opinion) | 0.52 | Changes with moderate evidence |
| 0.5 (moderate trait) | 0.625 | Requires strong, repeated evidence |
| 0.7 (significant value) | 0.745 | Near-certain contradictory evidence needed |
| 0.9 (core belief) | 0.905 | Requires overwhelming, multi-session evidence |
| 1.0 (immutable policy) | 1.0 | Never updates (safety policies) |

### 6.4 Contradiction Detection Mechanism

This was the gap in the original design. Here is the full mechanism:

```python
def detect_identity_contradiction(
    incoming_message: str,
    conversation_context: list[ConversationTurn],
    identity_store: list[IdentityMemory]
) -> list[IdentityContradiction]:
    """
    Runs after each session to detect whether user interaction
    produced evidence that contradicts any identity belief.
    """
    contradictions = []

    for belief in identity_store:
        if belief.is_immutable:
            continue

        # Embed the incoming evidence
        evidence_embedding = embed(conversation_context[-10:])  # last 10 turns
        belief_embedding = embed(belief.statement)

        # Semantic contradiction score: high similarity + opposing polarity
        similarity = cosine_similarity(evidence_embedding, belief_embedding)
        polarity_mismatch = detect_polarity_opposition(
            conversation_context, belief.statement
        )

        contradiction_score = similarity * polarity_mismatch

        if contradiction_score > 0.6:
            contradictions.append(IdentityContradiction(
                belief_id=belief.belief_id,
                evidence_summary=summarize_turns(conversation_context[-10:]),
                contradiction_score=contradiction_score,
                session_id=current_session_id
            ))

    return contradictions

def apply_identity_update(belief: IdentityMemory, contradiction: IdentityContradiction):
    evidence_strength = contradiction.contradiction_score
    # Only update if cumulative evidence across sessions crosses threshold
    total_evidence = sum(e.strength for e in belief.evidence_against) + evidence_strength

    if total_evidence >= belief.update_threshold and not belief.is_immutable:
        # Log the update
        belief.update_history.append(BeliefUpdateEvent(
            prior_statement=belief.statement,
            new_statement=generate_updated_belief(belief, contradiction),
            triggering_session_id=contradiction.session_id,
            evidence_strength=evidence_strength,
            update_reason=contradiction.evidence_summary
        ))
        # Apply update
        belief.statement = generate_updated_belief(belief, contradiction)
        belief.last_updated = datetime.utcnow()
```

### 6.5 Immutable Policies

Some identity beliefs are flagged `is_immutable = True` at initialization and can never be updated by any conversation. These are safety-critical behavioral policies:

- "Nova does not claim to be human when directly and sincerely asked"
- "Nova does not provide medical diagnoses"
- "Nova does not generate content that sexualizes minors"
- "Nova always surfaces crisis resources when self-harm risk is detected"
- "Nova does not claim certainty about user's inner emotional state"

These policies live in Identity Memory but have a separate hard-coded enforcement path in the Safety Agent (Layer 11) — which also owns crisis detection and crisis-resource surfacing — that is independent of the identity retrieval pipeline. (Layer 8 is Tool Use & Actions, not crisis; Layer 9 is Output Delivery; the older "Safety Layer (Layer 9)" numbering is corrected here.)

---

## 7. Sub-Component 5 — User World Model

### 7.1 Purpose

The User World Model (UWM) is the most structurally important sub-component that was previously undesigned. It is the system's live, structured representation of the user as a *person in the world* — not just a source of conversational input, but a human being with relationships, career context, ongoing life situations, recurring emotional patterns, and a social graph.

Every other layer that operates on social context (Layer 5 Social Coaching, Layer 6 Proactivity, Layer 7 Goal Detection) reads from the UWM. Without it, those layers operate on impoverished self-reported context. With it, they operate on a structured, continuously updated model of the user's life.

### 7.2 Top-Level Schema

```python
class UserWorldModel:
    user_id: UUID
    created_at: datetime
    last_updated_at: datetime
    update_version: int                   # increments on each write

    # Core Identity
    profile: UserProfile

    # Relational World
    relationship_graph: RelationshipGraph

    # Life Context
    life_context: LifeContext

    # Psychological Model
    psychological_model: PsychologicalModel

    # Communication Model
    communication_model: CommunicationModel

    # Data Sources
    data_sources: list[Literal["self_reported", "inferred_from_episodic", "social_graph_layer"]]
    confidence_by_field: dict[str, float]  # field path → confidence 0–1
```

### 7.3 UserProfile Schema

```python
class UserProfile:
    # Self-reported or inferred basics
    preferred_name: Optional[str]
    inferred_age_range: Optional[str]     # "18–22", "25–30" — never exact
    pronouns: Optional[str]
    location_context: Optional[str]       # "college campus in Bengaluru" — semantic, not GPS
    primary_language: str
    secondary_languages: list[str]

    # Academic / Career
    current_life_stage: Literal[
        "school", "undergraduate", "postgraduate",
        "early_career", "mid_career", "career_transition",
        "gap_period", "unknown"
    ]
    field_of_study_or_work: Optional[str]  # "Computer Science", "Design", etc.
    institution_or_employer: Optional[str]
    current_academic_year: Optional[str]   # "2nd year", "final year"
    career_goals_summary: Optional[str]    # brief synthesis of expressed career direction

    # Living Situation (inferred)
    likely_living_situation: Optional[Literal[
        "family_home", "college_hostel", "shared_apartment",
        "alone", "unknown"
    ]]
```

### 7.4 RelationshipGraph Schema

```python
class RelationshipGraph:
    user_id: UUID
    people: list[PersonNode]
    last_updated: datetime

class PersonNode:
    person_id: UUID
    name: str                             # as user refers to them
    aliases: list[str]                    # nicknames, alternate references
    relationship_tier: Literal[
        "close_friend",
        "friend",
        "acquaintance",
        "family_close",                   # parent, sibling, partner
        "family_extended",
        "romantic_partner",
        "ex_partner",
        "colleague",
        "mentor_advisor",
        "authority_figure",               # professor, boss, landlord
        "rival_or_adversary",
        "unclear"
    ]
    first_mentioned_at: datetime
    last_mentioned_at: datetime
    mention_count: int
    inferred_traits: list[str]            # ["supportive", "critical", "unreliable"]
    emotional_significance_to_user: float # 0–1; how much user seems to care about this person
    current_relationship_valence: float   # –1 (strained) to +1 (positive)
    is_active_in_user_life: bool          # has been mentioned in last 60 days
    source_episode_ids: list[UUID]        # episodic memories where this person appears
    notes: list[str]                      # brief narrative notes about this relationship
```

**`RelationshipEdge`/`SentimentPoint` removed from the spec (2026-08-10, §19 Live Wiring
Status).** Never constructed by `uwm_updater.py` and never read anywhere — genuine duplication
with Layer 5's `SocialEdge` (tie strength, shared contexts, sentiment trend), which is the live
owner of per-person relationship-edge data. `PersonNode` already carries the scalar
`current_relationship_valence`/`emotional_significance_to_user` this layer actually uses; the
time-series edge concept belongs to Layer 5, not duplicated here.

### 7.5 LifeContext Schema

```python
class LifeContext:
    # Active situations (things currently happening)
    active_situations: list[LifeSituation]

    # Life timeline (major events)
    life_events: list[LifeEvent]

    # Current stressors
    active_stressors: list[Stressor]

class LifeSituation:
    situation_id: UUID
    description: str                      # "Preparing for placements season"
    category: Literal[
        "academic", "career", "relationship", "health",
        "family", "financial", "creative", "identity", "other"
    ]
    started_at: datetime
    estimated_resolution: Optional[datetime]
    emotional_weight: float               # 0–1
    status: Literal["active", "resolved", "stalled", "monitoring"]
    related_episode_ids: list[UUID]
```

**`RecurringTheme` removed from the spec (2026-08-10, §19 Live Wiring Status).** Never
constructed by `uwm_updater.py` and never read anywhere; no extraction logic exists to populate
it, and nothing downstream would consume it if it did — deleted rather than wired for its own
sake, per CLAUDE.md's prefer-wiring-unless-genuinely-over-engineered rule.

```python
class LifeEvent:
    event_id: UUID
    description: str
    category: str
    occurred_at: datetime
    emotional_impact: float               # –1 to +1 (negative to positive)
    is_milestone: bool                    # True for significant life moments

class Stressor:
    stressor_id: UUID
    description: str
    intensity: float                      # 0–1
    duration_days: int
    category: str
    linked_situation_id: Optional[UUID]
```

### 7.6 PsychologicalModel Schema

```python
class PsychologicalModel:
    # Communication tendencies
    attachment_signals: list[str]         # inferred from communication patterns; not diagnostic
    # e.g. ["seeks reassurance before acting", "pulls back when overwhelmed"]

    # Emotional regulation patterns
    emotional_regulation_style: Optional[Literal[
        "expressive_processor",           # talks through emotions at length
        "intellectualizer",               # converts emotion to analysis
        "minimizer",                      # downplays emotional content
        "delayed_discloser",              # takes multiple sessions to open up
        "direct_expresser"               # states emotions plainly
    ]]

    # Response to support
    preferred_support_style: Optional[Literal[
        "validation_first",               # needs to feel heard before solutions
        "solution_oriented",              # wants practical steps quickly
        "co_thinking",                    # wants to reason through together
        "space_giver"                     # prefers Nova to listen more than respond
    ]]

    # Self-perception signals (inferred, not diagnostic)
    self_efficacy_signals: list[str]      # patterns suggesting high/low confidence
    identity_conflict_signals: list[str]  # tensions in how user sees themselves

    # Trigger patterns (things that reliably produce strong responses)
    known_triggers: list[TriggerPattern]

    # Confidence qualifiers — all fields in PsychologicalModel carry uncertainty
    model_confidence: float               # 0–1; low until 20+ sessions
    last_updated: datetime
    derived_from_episode_count: int

class TriggerPattern:
    trigger_id: UUID
    description: str                      # "Being told what to do without explanation"
    response_type: str                    # "withdrawal", "irritation", "anxiety spike"
    evidence_count: int
    last_observed_at: datetime
```

### 7.7 CommunicationModel Schema

```python
class CommunicationModel:
    # Language style
    vocabulary_complexity: Literal["simple", "moderate", "technical", "mixed"]
    typical_message_length: Literal["brief", "moderate", "verbose"]
    uses_slang: bool
    uses_humor: bool
    humor_style: Optional[str]            # "dry", "self-deprecating", "absurdist"
    code_switches_language: bool          # uses multiple languages in messages

    # Conversational preferences
    prefers_direct_answers: bool
    tolerates_tangents: bool
    engages_with_questions: bool          # responds well when Nova asks back
    prefers_nova_to_initiate: bool        # or waits for user to lead

    # Temporal patterns
    peak_engagement_bands: list[str]      # circadian bands with most engagement
    average_session_duration_minutes: float
    response_latency_profile: str         # "reactive", "considered", "variable"

    # Calibration
    last_updated: datetime
    sessions_used_for_calibration: int
```

### 7.8 UWM Update Logic

The UWM is updated by the State Updater at session end, not during inference. This prevents the model from being updated mid-conversation in ways that might affect the current response.

```python
def update_user_world_model(
    uwm: UserWorldModel,
    session_episodes: list[EpisodicMemory],
    conversation_turns: list[ConversationTurn],
    layer1_packet: InputPerceptionPacket
) -> UserWorldModel:
    """
    Called by State Updater after session end.
    Updates UWM based on session content.
    """
    # 1. Extract new person mentions → update RelationshipGraph
    new_people, updated_edges = extract_relationship_signals(conversation_turns)
    uwm.relationship_graph = merge_relationship_updates(uwm.relationship_graph, new_people, updated_edges)

    # 2. Detect life situation updates
    situation_updates = detect_situation_changes(session_episodes, uwm.life_context)
    uwm.life_context = apply_situation_updates(uwm.life_context, situation_updates)

    # 3. Update communication model from session behavior
    uwm.communication_model = update_communication_model(
        uwm.communication_model, layer1_packet, conversation_turns
    )

    # 4. Update psychological model patterns (runs every 5 sessions, not every session)
    if should_update_psychological_model(uwm):
        uwm.psychological_model = reanalyze_psychological_patterns(
            uwm.psychological_model, session_episodes
        )

    uwm.last_updated_at = datetime.utcnow()
    uwm.update_version += 1
    return uwm
```

### 7.9 UWM Retrieval Interface

Downstream layers query the UWM through a typed interface:

```python
def query_uwm(user_id: UUID, query_type: str, context: str = "") -> dict:
    """
    Downstream layers call this; never access UWM directly.
    """
    uwm = load_uwm(user_id)

    if query_type == "relationship_context":
        # Returns: relevant PersonNodes + edge sentiment for people mentioned in context
        return extract_relationship_context(uwm, context)

    elif query_type == "active_stressors":
        # Returns: current stressors + emotional weight
        return uwm.life_context.active_stressors

    elif query_type == "communication_preferences":
        # Returns: communication model for persona/response shaping
        return uwm.communication_model

    elif query_type == "psychological_posture":
        # Returns: support style preference + known triggers
        return {
            "support_style": uwm.psychological_model.preferred_support_style,
            "triggers": uwm.psychological_model.known_triggers
        }

    elif query_type == "life_stage_context":
        # Returns: profile + active situations summary
        return {
            "profile": uwm.profile,
            "active_situations": uwm.life_context.active_situations
        }
```

---

## 8. Sub-Component 6 — Recall Scoring Engine

### 8.1 Purpose

The Recall Scoring Engine answers the question: *given what the user just said, and given who they are and how they feel right now, which memories are most relevant to surface?*

Memory retrieval is not a lookup. It is a **competition** governed by four simultaneously weighted signals. This is the mathematical core of Layer 2.

### 8.2 The Four-Component Recall Score

For each candidate memory `m`, given query `q`, current emotional state `e`, and current time `t`:

```
RecallScore(m, q, e, t) = α·Semantic(m,q) + β·Emotional(m,e) + γ·Temporal(m,t) + δ·Importance(m)

where α + β + γ + δ = 1
Default weights: α=0.40, β=0.30, γ=0.20, δ=0.10
```

**Component 1 — Semantic(m, q):**
```
Semantic(m, q) = cosine_similarity(embed(q), m.embedding)
```
Standard vector similarity. The query `q` is not just the last message — it is a composite of: last message content (60%) + session topic summary (30%) + due narrative thread summaries (10%). This prevents single-message over-fitting.

**Component 2 — Emotional(m, e):**
```
Emotional(m, e) = exp(–λ_e · ||m.emotion_vector – e||²)
```
Where `e` is the current user emotional state (valence-arousal vector from Layer 3) and `m.emotion_vector` is the state at memory creation. λ_e = 2.0 (default tuning parameter).

This implements **mood-congruent recall**: when a user is distressed, memories formed during past distress score higher. When they're happy, positive memories surface. This is a well-documented human memory phenomenon implemented as a first-class scoring term.

**Component 3 — Temporal(m, t):**
```
Temporal(m, t) = exp(–decay_rate(m) · (t – m.created_at))
```
Recent memories score higher. But high-importance memories decay slower — a life event from 6 months ago can outcompete a trivial exchange from yesterday. The decay rate is the same λ computed in the Memory Strength model: `λ = base_decay × (1 – importance)`.

**Component 4 — Importance(m):**
```
Importance(m) = m.importance_score × m.S_current
```
A high-importance memory that has nearly decayed (low `S_current`) scores modestly here. A high-importance memory with high current strength scores maximally. This is the "historical significance × current vitality" product.

### 8.3 Memory Strength Decay Model

Initial strength at creation:
```
S₀ = w₁·BaseImportance + w₂·EmotionalWeight + w₃·Novelty
where w₁=0.5, w₂=0.3, w₃=0.2
```

Decay over time:
```
S(t) = S₀ · exp(–λt)
λ = base_decay × (1 – importance_score)
base_decay = 0.10 (default)
```

Reinforcement follows logarithmic returns (prevents runaway accumulation):
```
S_new = S_old + log(1 + reinforcement_signal)
reinforcement_signal ∈ [0, 1] based on recall context strength
```

**Deletion vs. archival:**
- `S(t) < 0.1 AND importance < 0.5` → **delete**
- `S(t) < 0.1 AND importance ≥ 0.5` → **archive** (retrievable under strong cue, not surfaced normally)

### 8.4 Competitive Recall via Softmax

Candidate memories are scored, then selected probabilistically:

```
P(recall_i) = softmax(RecallScore_i / τ)
```

Temperature `τ` controls recall predictability:

| τ value | Behavior | Use case |
|---|---|---|
| 0.3 | 80% → highest scorer; near-deterministic | Technical/factual queries |
| 0.5 | 65% → highest scorer; moderate variation | General conversation |
| 0.7 (default) | 50% → highest scorer; natural variation | Emotional/relational conversation |
| 1.2 | Near-random; broad recall | Exploratory / creative conversation |

τ is set dynamically by context mode (see §8.5). It is not a fixed global setting.

### 8.5 Context Gating

Even well-scored memories should not always fire. The context gate modulates the effective recall score:

```
EffectiveScore(m) = RecallScore(m, q, e, t) × S(t) × G(context, memory_type)
```

The gate G is a lookup table:

| Conversation Mode | Episodic (emotional) | Episodic (factual) | Semantic | Identity |
|---|---|---|---|---|
| `casual` | 0.10 | 0.20 | 0.50 | 0.20 |
| `emotional_support` | 1.00 | 0.30 | 0.60 | 0.20 |
| `crisis` | 1.00 | 0.10 | 0.40 | 0.10 |
| `celebration` | 0.90 | 0.30 | 0.50 | 0.20 |
| `technical_discussion` | 0.10 | 0.70 | 0.80 | 0.30 |
| `goal_planning` | 0.40 | 0.70 | 0.90 | 0.30 |
| `social_coaching` | 0.60 | 0.50 | 0.80 | 0.20 |
| `life_review` | 0.90 | 0.90 | 0.70 | 0.30 |

Conversation mode is determined by Layer 3 (Intent & Emotion Classifier) and is passed to the Memory Arbiter as part of the classification packet. The mode keys are Layer 3's **canonical eight-mode taxonomy**: this table is reconciled from the doc's older `casual_small_talk` → `casual` and `crisis_detected` → `crisis` spellings, and the previously-missing `celebration` row was added (emotion-forward, like `emotional_support` but with factual recall kept low — the moment, not the record). An episodic memory is classified `episodic_emotional` when its `emotional_weight ≥ 0.4`, else `episodic_factual`.

### 8.6 Retrieval Caps and Output Format

```python
class RecallResult:
    memories: list[ScoredMemory]   # max 3 per call; sorted by EffectiveScore descending
    uwm_context: dict              # relevant UWM fields for the current query
    total_candidates_evaluated: int
    retrieval_mode: str            # conversation mode used
    temperature_used: float

class ScoredMemory:
    memory: EpisodicMemory | SemanticMemory
    recall_score: float
    effective_score: float
    gate_value: float
    components: dict               # {semantic: 0.72, emotional: 0.45, temporal: 0.88, importance: 0.80}
    fuzzy_temporal_label: str      # "a few weeks ago"
```

**Cap enforcement:** Maximum 3 memories per retrieval call. More than 3 makes Nova feel omniscient and creepy. Fewer than 1 makes it feel like it forgot. The gate + cap together maintain this balance.

---

## 9. Sub-Component 7 — Forgetting & Consolidation Engine

### 9.1 Purpose

The Forgetting & Consolidation Engine (FCE) is how Nova learns without fine-tuning. It runs periodically — not per message — and performs three operations: decay sweep, cluster detection, and semantic extraction. The result is that repeated episodic patterns are compressed into stable semantic facts, and irrelevant episodic memories are deleted.

### 9.2 Trigger Conditions

The FCE is triggered under any of the following conditions (whichever comes first):

| Trigger | Condition |
|---|---|
| Episode count threshold | New episodic memories since last run ≥ 50 |
| Interaction count threshold | Sessions since last run ≥ 25 |
| Calendar interval | 14 days since last run regardless of count |
| Manual trigger | User requests memory review via Layer 12 Memory Audit Tool |
| Pre-deletion trigger | User initiates memory deletion; FCE runs first to show cascade impact |

FCE runs in a **background job** — it does not block any conversation. It is scheduled via a task queue (Celery + Redis, or WorkManager on Android) and runs during charging/idle periods.

### 9.3 Step 1 — Decay Sweep

```python
def decay_sweep(user_id: UUID, now: datetime):
    episodes = load_all_episodic_memories(user_id)

    for episode in episodes:
        # Recompute current strength
        time_elapsed = (now - episode.last_decay_computed_at).days
        episode.S_current = episode.S_current * math.exp(
            -episode.decay_rate * time_elapsed
        )
        episode.last_decay_computed_at = now

        # Deletion vs. archival decision
        if episode.S_current < 0.1:
            if episode.importance_score < 0.5:
                mark_for_deletion(episode)
                log_audit(
                    memory_id=episode.memory_id,
                    action="deleted_by_decay",
                    reason=f"S(t)={episode.S_current:.3f}, importance={episode.importance_score:.2f}",
                    timestamp=now
                )
            else:
                episode.is_archived = True
                log_audit(
                    memory_id=episode.memory_id,
                    action="archived_by_decay",
                    reason=f"S(t)={episode.S_current:.3f}, importance={episode.importance_score:.2f} (above deletion threshold)",
                    timestamp=now
                )
```

### 9.4 Step 2 — Cluster Detection

```python
def cluster_detection(user_id: UUID) -> list[EpisodicCluster]:
    active_episodes = load_active_episodic_memories(user_id)
    embeddings = [e.embedding for e in active_episodes]

    # Agglomerative clustering with cosine distance threshold
    # Cluster only forms if cosine similarity > 0.85 between all members
    clusters = agglomerative_cluster(
        embeddings,
        threshold=0.85,
        linkage="complete"      # all-pairs similarity; prevents chaining
    )

    # Only return clusters with ≥ 3 members (pattern requires repetition)
    return [c for c in clusters if len(c.members) >= 3]
```

**Clustering algorithm choice:** Agglomerative clustering with complete linkage is used because:
- It produces compact, well-separated clusters (complete linkage ensures every pair in a cluster is similar, not just nearest-neighbor chains)
- It requires no pre-specified cluster count
- It is deterministic given the same input
- It naturally handles variable cluster sizes

Threshold of 0.85 cosine similarity means only highly semantically related memories cluster — "exam anxiety in session 4" and "exam anxiety in session 7" cluster together, but "exam anxiety" and "general work stress" do not.

### 9.5 Step 3 — Semantic Extraction

```python
def extract_semantic_memory(cluster: EpisodicCluster, user_id: UUID) -> SemanticMemory:
    # Use LLM to generate a stable generalization from the cluster
    cluster_summaries = [e.summary for e in cluster.members]

    # Prompt: "These are recurring observations about a user. Generate one concise,
    # stable generalization that captures the common pattern."
    generalization = llm_generalize(cluster_summaries)

    # Determine memory type from cluster topic tags
    dominant_tags = get_dominant_tags(cluster.members)
    memory_type = classify_semantic_type(dominant_tags)

    new_semantic = SemanticMemory(
        memory_id=uuid4(),
        user_id=user_id,
        memory_type=memory_type,
        statement=generalization,
        confidence=compute_initial_confidence(len(cluster.members)),
        # confidence = 0.5 + (0.05 × cluster_size), capped at 0.95
        supporting_episode_ids=[e.memory_id for e in cluster.members],
        evidence_count=len(cluster.members),
        created_at=datetime.utcnow(),
        last_confirmed_at=cluster.most_recent_episode.created_at,
        decay_rate=0.005   # very slow; semantic facts are stable
    )

    # Delete the consolidated episodic memories
    for episode in cluster.members:
        episode.consolidated_into = new_semantic.memory_id
        mark_for_deletion(episode)
        log_audit(
            memory_id=episode.memory_id,
            action="consolidated_into_semantic",
            reason=f"Cluster of {len(cluster.members)} similar episodes → semantic: {new_semantic.memory_id}",
            timestamp=datetime.utcnow()
        )

    return new_semantic
```

### 9.6 FCE Output Report

After each FCE run, a report is written to the audit trail and made available to the Layer 12 Memory Audit Tool:

```python
class FCERunReport:
    run_id: UUID
    user_id: UUID
    run_at: datetime
    trigger_reason: str
    episodes_evaluated: int
    episodes_deleted: int
    episodes_archived: int
    clusters_detected: int
    semantic_memories_created: int
    episodes_consolidated: int
    new_semantic_summaries: list[str]
    next_scheduled_run: datetime
```

---

## 10. Sub-Component 8 — Memory Audit Trail

### 10.1 Purpose

The Memory Audit Trail is the complete, tamper-evident log of every memory lifecycle event: why a memory was created, recalled, reinforced, updated, archived, or deleted. It serves two purposes:
1. **Transparency**: the Layer 12 Memory Audit Tool exposes this log to the user, allowing them to understand and contest what Nova remembers
2. **System integrity**: the audit trail enables reproducible debugging — every Nova behavior traceable to a memory can be investigated

### 10.2 Audit Event Schema

```python
class AuditEvent:
    event_id: UUID
    user_id: UUID
    timestamp: datetime
    event_type: Literal[
        "memory_created",
        "memory_recalled",
        "memory_reinforced",
        "memory_updated",
        "memory_archived",
        "memory_deleted_by_decay",
        "memory_deleted_by_user",
        "memory_consolidated",
        "semantic_memory_created",
        "semantic_memory_deprecated",
        "identity_belief_updated",
        "uwm_updated",
        "uwm_field_updated",
        "recall_attempted_no_result",
        "context_gate_suppressed_recall"
    ]
    memory_id: Optional[UUID]           # which memory this event concerns
    session_id: Optional[UUID]          # session context if applicable

    # Event-specific details
    reason: str                         # human-readable explanation
    score_at_event: Optional[float]     # recall score if applicable
    prior_value: Optional[str]          # before value if update/deprecation
    new_value: Optional[str]            # after value if update/deprecation
    triggered_by: str                   # "state_updater", "fce", "user_request", "recall_engine"

    # Integrity
    content_hash: str                   # SHA-256 of the event data (tamper detection)
    prev_event_hash: str                # hash of previous event (chain integrity)
```

The hash chain (`content_hash` ← `prev_event_hash`) forms a lightweight audit log integrity proof. Modifying a past event invalidates all subsequent hashes, making tampering detectable.

### 10.3 Cross-Session Narrative Linking

This was the second gap in the original design. Episodes are not just isolated records — they are connected to each other through a narrative link graph that allows Nova to reason about the *arc* of a situation across multiple sessions.

```python
class NarrativeLinkGraph:
    user_id: UUID
    chains: list[NarrativeChain]

class NarrativeChain:
    chain_id: UUID
    theme: str                          # "Placement anxiety → interview preparation → result"
    episodes: list[ChainedEpisode]      # ordered chronologically
    status: Literal["active", "resolved", "stalled", "archived"]
    first_episode_at: datetime
    last_episode_at: datetime
    arc_summary: Optional[str]          # generated by FCE: 1-para narrative summary of the arc

class ChainedEpisode:
    episode_id: UUID
    position_in_chain: int
    link_type: Literal[
        "continuation",       # same situation progressing
        "escalation",         # situation intensifying
        "resolution",         # situation resolved
        "relapse",            # previously resolved situation recurs
        "reframing",          # user's interpretation of situation changed
        "new_development"     # unexpected new development in ongoing situation
    ]
    linked_at: datetime
```

**Link detection logic (runs in State Updater after each session):**

```python
def detect_narrative_links(
    new_episode: EpisodicMemory,
    existing_chains: list[NarrativeChain]
) -> Optional[NarrativeChain]:
    """
    Check if a new episode continues an existing narrative chain.
    """
    for chain in existing_chains:
        if chain.status in ["resolved", "archived"]:
            continue

        # Compare new episode to last episode in chain
        last_episode = load_episode(chain.episodes[-1].episode_id)
        semantic_similarity = cosine_similarity(
            new_episode.embedding, last_episode.embedding
        )

        # Also check entity overlap (same people mentioned)
        entity_overlap = len(
            set(new_episode.entity_refs) & set(last_episode.entity_refs)
        ) / max(len(new_episode.entity_refs), 1)

        link_score = 0.6 * semantic_similarity + 0.4 * entity_overlap

        if link_score > 0.65:
            # Classify link type
            link_type = classify_link_type(new_episode, last_episode)
            chain.episodes.append(ChainedEpisode(
                episode_id=new_episode.memory_id,
                position_in_chain=len(chain.episodes),
                link_type=link_type,
                linked_at=datetime.utcnow()
            ))
            chain.last_episode_at = new_episode.created_at
            if link_type == "resolution":
                chain.status = "resolved"
            return chain

    # No existing chain matched; create new chain with this episode as seed
    return None
```

### 10.4 Memory Audit Tool Interface (Layer 12 Integration Point)

The Audit Trail exposes a query interface to the Layer 12 Memory Audit Tool:

```python
def query_audit_trail(
    user_id: UUID,
    filter: AuditQueryFilter
) -> list[AuditEvent]:
    """
    Used by Layer 12 to power the user-facing memory transparency tool.
    """

class AuditQueryFilter:
    event_types: Optional[list[str]]
    memory_id: Optional[UUID]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    triggered_by: Optional[str]
    limit: int = 100
```

---

## 11. The Memory Arbiter — Orchestration Logic

### 11.1 Purpose

The Memory Arbiter is the single interface through which all other layers access Layer 2. It receives a query from the Conversation Orchestrator, calls the appropriate sub-components, and returns a `MemoryPacket`.

No downstream agent calls a memory sub-component directly.

### 11.2 Arbiter Execution Sequence

**As-built note (Polish Phase 2):** the pseudocode below takes `emotion_classification` "from
Layer 3" and a resolved `conversation_mode`, but `docs/NOVA_AI_MASTER_ARCHITECTURE.md` §3 and the
actual orchestrator (`backend/pipeline/conversation_orchestrator.py`) both run Layer 2 recall at
step 3, *before* Layer 3 classification at step 5 — by design, not oversight (recall needs to
inform the same turn's generation, and classification depends on more than recall does). Neither
signal exists yet when `memory_arbiter` runs. In production: `conversation_mode` falls back to
the configured `default_mode` (there is genuinely no earlier mode signal — this is an honest
gap, not fixed); `emotional_state` is derived from Layer 1's `composite_emotional_prior` /
`prior_confidence` (a `[0,1]` pre-linguistic vulnerability signal, not Layer 3's richer
valence/arousal output) via `api/assembly.py::_emotion_from_input_packet`. See §19.

```python
async def memory_arbiter(
    user_id: UUID,
    layer1_packet: InputPerceptionPacket,
    emotion_classification: EmotionClassification,  # spec intent; as-built uses Layer 1's prior — see note above
    conversation_mode: str
) -> MemoryPacket:

    # 1. Load STM buffer (current session)
    stm = load_stm(user_id, layer1_packet.session_id)

    # 2. Determine query for long-term recall
    query = build_recall_query(
        current_message=layer1_packet.modality_context.raw_text,
        stm=stm,
        due_threads=layer1_packet.due_threads
    )

    # 3. Run recall scoring engine
    recall_result = recall_scoring_engine(
        user_id=user_id,
        query=query,
        emotional_state=emotion_classification.emotion_vector,
        conversation_mode=conversation_mode,
        now=layer1_packet.received_at
    )

    # 4. Query User World Model for relevant context
    uwm_context = query_uwm(user_id, "life_stage_context") |                   query_uwm(user_id, "relationship_context", query) |                   query_uwm(user_id, "psychological_posture")

    # 5. Retrieve relevant narrative chain if applicable
    active_chains = get_active_narrative_chains(user_id)

    # 6. Assemble MemoryPacket
    return MemoryPacket(
        stm_turns=stm.turns[-10:],             # last 10 turns for immediate context
        recalled_memories=recall_result.memories,
        uwm_context=uwm_context,
        active_narrative_chains=active_chains,
        retrieval_metadata=recall_result,
        fuzzy_label_util=layer1_packet.fuzzy_label_for_timestamp
    )
```

### 11.3 MemoryPacket — Full Output Schema

This is the formal contract Layer 2 hands to all downstream layers.

```python
class MemoryPacket:
    # Current session context
    stm_turns: list[ConversationTurn]      # last 10 turns; full in-session context

    # Long-term recall
    recalled_memories: list[ScoredMemory]  # max 3; scored and gated

    # User World Model snapshot
    uwm_context: UWMContextSnapshot        # relevant slice of UWM for this query

    # Narrative context
    active_narrative_chains: list[NarrativeChain]  # chains involving current topics

    # Metadata (for audit trail + debugging)
    retrieval_metadata: RecallResult

    # Utility
    fuzzy_label_util: Callable[[datetime], str]  # timestamp → human label

class UWMContextSnapshot:
    user_profile_brief: str               # 2-3 sentence life context summary
    relevant_people: list[PersonNode]     # people relevant to current conversation
    active_stressors: list[Stressor]
    active_situations: list[LifeSituation]
    psychological_posture: dict           # support style + triggers
    communication_preferences: CommunicationModel
```

---

## 12. State Updater — Write Path

### 12.1 Purpose

All writes to Layer 2's memory stores go through the State Updater, which runs **after** the full conversation turn completes. This separation ensures:
- Layer 2 is read-only during inference (no mid-turn memory mutations)
- All writes are atomic (session either fully committed or fully rolled back)
- The audit trail captures the complete post-session state

### 12.2 State Updater Execution Sequence

```python
def state_updater(
    user_id: UUID,
    session_id: UUID,
    stm_buffer: ShortTermMemoryBuffer,
    layer1_packet: InputPerceptionPacket,
    emotion_classification: EmotionClassification,
    conversation_mode: str
):
    """Runs after each full conversation turn (not each message)."""

    # 1. Episodic memory extraction from STM
    new_episodes = extract_episodes_from_stm(stm_buffer, emotion_classification)
    for episode in new_episodes:
        save_episodic_memory(episode)
        log_audit(event_type="memory_created", memory_id=episode.memory_id, ...)

    # 2. Reinforce recalled memories
    for scored_memory in last_recall_result.memories:
        if scored_memory.was_used_in_response:
            reinforce_memory(scored_memory.memory.memory_id)
            log_audit(event_type="memory_reinforced", ...)

    # 3. Update NarrativeThread status
    for thread in layer1_packet.due_threads:
        if thread_was_addressed_in_session(thread, stm_buffer):
            thread.status = "resolved"
            save_narrative_thread(thread)

    # 4. Create/update narrative chain links
    for episode in new_episodes:
        link_to_chain = detect_narrative_links(episode, get_active_chains(user_id))
        if link_to_chain:
            save_narrative_chain(link_to_chain)

    # 5. Update User World Model
    uwm = load_uwm(user_id)
    uwm = update_user_world_model(uwm, new_episodes, stm_buffer.turns, layer1_packet)
    save_uwm(uwm)
    log_audit(event_type="uwm_updated", ...)

    # 6. Check identity contradiction (runs on identity-relevant sessions)
    contradictions = detect_identity_contradiction(
        stm_buffer.turns, load_identity_memory(user_id)
    )
    for contradiction in contradictions:
        apply_identity_update(load_belief(contradiction.belief_id), contradiction)
        log_audit(event_type="identity_belief_updated", ...)

    # 7. Schedule FCE if trigger conditions met
    if should_trigger_fce(user_id):
        schedule_fce_background_job(user_id)
```

---

## 13. Storage Architecture

| Store | Backend | Data | Encryption | Location |
|---|---|---|---|---|
| Episodic Memory | SQLite metadata + hnswlib (`memory.vdb`) | Episode records + 384-dim embeddings | SQLCipher / AES-256-GCM at rest | On-device (primary) / Cloud (opt-in, client-side encrypted) |
| Semantic Memory | SQLite + hnswlib | Semantic facts + embeddings | SQLCipher at rest | On-device / Cloud opt-in |
| Identity Memory | SQLite | Belief records | AES-256 at rest | Cloud (Nova's identity, not user-private) |
| User World Model | SQLite (JSON columns) | Structured user model | SQLCipher at rest | On-device only |
| Short-Term Buffer | RAM | Session turns | None (in-memory) | On-device only |
| Audit Trail | SQLite (append-only) | Audit events + hash chain | SQLCipher at rest | On-device + encrypted cloud backup |
| Narrative Chain Graph | SQLite | Chain records + links | SQLCipher at rest | On-device / Cloud opt-in |

All persistent stores are **on-device, in-process — no PostgreSQL server or network**. (The
earlier "pgvector / PostgreSQL" backend is superseded by the on-device SQLite + hnswlib stack
that the rest of the architecture, CLAUDE.md, and Layer 12 specify.)

**On-device vs. cloud policy:**
- User World Model: **on-device only, never cloud** (most sensitive; contains relationship graph)
- Episodic Memory: on-device by default; cloud sync requires explicit consent and uses client-side encryption (cloud sees only encrypted blobs)
- Semantic Memory: same as episodic
- Identity Memory: cloud (it's Nova's model, not the user's private data)
- Audit Trail: on-device primary; encrypted cloud backup for recovery (cloud cannot read content)

---

## 14. Downstream Consumption Contract

| Layer | Fields Consumed | Purpose |
|---|---|---|
| **Layer 3** (Emotion) | `recalled_memories`, `stm_turns` | Emotional context for current response |
| **Layer 4** (Persona) | `uwm_context.communication_preferences`, `recalled_memories` | Tone and language calibration |
| **Layer 5** (Social) | `uwm_context.relevant_people`, `uwm_context.active_stressors`, `active_narrative_chains` | Social coaching context; relationship-aware responses |
| **Layer 6** (Proactivity) | `active_narrative_chains`, `uwm_context.active_situations` | Detect threads worth following up proactively |
| **Layer 7** (Goals) | `uwm_context.user_profile_brief`, `active_narrative_chains`, `recalled_memories` | Goal context; life event detection |
| **Layer 9** (Safety) | `recalled_memories` (emotional type), `active_narrative_chains` | Crisis pattern detection; historical emotional context |
| **Layer 10** (Longitudinal) | `active_narrative_chains`, all episodic + semantic memories | Life arc reconstruction; retrospective generation |
| **Layer 12** (Privacy) | Audit Trail query interface | Memory transparency + deletion cascade |

**Fields never passed to the LLM as raw data:**
- `S_current` (memory strength as a float)
- `recall_score` or `effective_score` (as numbers)
- ISO timestamps
- `confidence` values from semantic memory

These are consumed by orchestration logic and translated into natural-language instructions for the LLM. The LLM receives *"User mentioned feeling overwhelmed about placements about two weeks ago — this was an emotionally significant moment"*, not *"EpisodicMemory(S_current=0.74, importance=0.78, emotional_weight=0.82)"*.

---

## 15. Error Handling and Fallback Behavior

| Failure Case | Fallback Behavior |
|---|---|
| Vector store unavailable | Return empty `recalled_memories`; flag `recall_degraded: True`; conversation proceeds with STM only |
| UWM load failure | Return empty `uwm_context`; flag `uwm_unavailable: True`; downstream layers operate without world model context |
| FCE job fails mid-run | Roll back to pre-FCE state; log failure; retry next trigger window |
| Identity contradiction detection failure | Skip identity update; log error; no conversation impact |
| Audit trail write failure | Log to local error file; do NOT block the conversation; retry on next session |
| New user (no memory yet) | Return empty `recalled_memories`; return skeletal UWM; flag `cold_start: True`; Layer 13 handles cold start posture |
| Memory retrieval returns 0 results above threshold | Return `recalled_memories = []`; flag `no_relevant_memories: True`; LLM prompt instructs Nova not to confabulate |

**Hard rule on confabulation prevention:** When `recalled_memories = []` or `no_relevant_memories: True`, the downstream prompt must include an explicit instruction: *"You have no recalled memories relevant to this query. Do not invent or imply specific memories. Respond as if this topic hasn't come up before unless the user explicitly states otherwise."*

---

## 16. Performance Targets

| Operation | Target Latency | Notes |
|---|---|---|
| STM load | < 1ms | RAM lookup |
| Recall scoring (50 candidates) | < 20ms | Vector similarity + arithmetic; CPU only |
| Recall scoring (500 candidates) | < 80ms | With HNSW index; still CPU-only |
| UWM query | < 5ms | PostgreSQL indexed read |
| State Updater (full run) | < 500ms | Runs post-response; does not block |
| FCE run (1000 episodes) | < 30 seconds | Background job; async |
| FCE run (10,000 episodes) | < 5 minutes | Background job; async |
| Audit trail write | < 2ms | Append-only insert |

---

## 17. Implementation Specification

### 17.1 Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| Vector store | hnswlib (in-process, on-device) | No server/network; cosine, `ef_construction=200`, `M=16`; behind a `VectorIndex` protocol |
| Embedding model | all-MiniLM-L6-v2 (384-dim) | 20ms on CPU; no GPU required; behind an `Embedder` protocol |
| Metadata store | SQLite + SQLCipher | Encrypted at rest; zero-configuration; on-device |
| Clustering | Agglomerative, complete linkage (pure-Python; scikit-learn optional) | Deterministic; threshold-based; no hard dependency |
| Background jobs | APScheduler (`background/scheduler.py`) / WorkManager (Android) | FCE runs async, never blocks a turn |
| Encryption at rest | AES-256-GCM | Industry standard; hardware-accelerated on modern chips |

### 17.2 Testing Requirements

| Test Category | Coverage Target | Method |
|---|---|---|
| Recall scoring formula | Component values correct for known inputs | Unit tests with synthetic memory sets |
| Softmax temperature behavior | Correct probability distribution at τ ∈ {0.3, 0.7, 1.2} | Statistical distribution test (1000 trials) |
| Decay rate correctness | S(t) values at t=1,7,30,90 days for all importance levels | Unit test with expected values |
| Context gate values | Correct gate applied per mode × memory_type combination | Unit test against lookup table |
| Consolidation correctness | Cluster of 3 similar episodes → semantic memory created | Integration test with synthetic episodes |
| UWM update idempotency | Running update twice produces same result | Property test |
| Audit trail integrity | Hash chain valid after 100 sequential events | Integrity verification test |
| Cross-session link detection | Link correctly detected for continuation, resolution, relapse | Integration test with multi-session fixtures |
| Confabulation guard | Empty recall → LLM prompt includes guard instruction | Integration test |
| Contradiction detection | Known contradicting evidence triggers belief update | Unit test |

---

## 18. Design Principles Summary

1. **Memory is a signal, not a store.** Every memory has strength, decay, and competition. The API never returns a memory — it returns a *scored* memory with its current vitality. No downstream agent treats memory recall as a lookup.

2. **Four signals compete, none dominates.** Semantic similarity, emotional resonance, temporal recency, and importance all contribute to recall. A memory that is emotionally resonant but semantically distant from the query can still win over a semantically relevant but emotionally flat one. That is the correct behavior.

3. **Mood-congruent recall is first-class.** The emotional component is not a post-hoc filter. It is baked into the recall score with a weight equal to 0.30. This is the architectural decision that makes Nova's memory feel *human* rather than *indexed*.

4. **The UWM is the most sensitive structure in Layer 2.** It contains the relationship graph — structured information about real people in the user's life. It is on-device only, never cloud-synced without explicit opt-in, and is the first thing deleted when the user requests account deletion.

5. **Write separation prevents mid-turn hallucination.** All writes go through the State Updater, which runs after the response is delivered. Memory is never mutated during inference. This means Nova cannot "learn" something and immediately contradict what it just said in the same response.

6. **The Audit Trail is the trust foundation.** Every memory lifecycle event is logged with a reason and a hash chain. The user can always see why a memory exists, why it was recalled, and why it was deleted. Opacity at the memory layer destroys trust faster than any other failure.

7. **Consolidation is learning.** The FCE is not a cleanup job. It is the mechanism by which repeated experience becomes stable knowledge. It is the only way Nova's understanding of the user improves without fine-tuning. It must run reliably, and its outputs must be audited.

---

## 19. Live Wiring Status (current state)

Layer 2 is implemented end-to-end in `backend/layer2_memory/`, pure-stdlib (no pgvector, no ORM,
no numpy). Heavy/non-deterministic dependencies sit behind protocols so the whole engine runs and
is tested offline; real backends drop in without touching engine code. Every module is used
somewhere — either by production wiring or by the module's own public API surface — with no
unreachable code, and all eight sub-components now have real production callers.

**Module map:**

| Module | Sub-component(s) | Notes |
|---|---|---|
| `schemas/` | all contract types | stdlib `@dataclass` + `str`-`Enum`; package split by sub-component (2026-08-10, see below) |
| `embedding.py` | vector infra | `cosine_similarity`; `Embedder`/`VectorIndex` protocols + deterministic/brute-force defaults (nomic-embed-text + ChromaDB in prod, not hnswlib/all-MiniLM — see below) |
| `memory_strength.py` | §8.3 | S0, decay, reinforcement, delete/archive |
| `recall_scorer.py` | SC-6 (§8.2) | four-component score; `RecallWeights` α=.40 β=.30 γ=.20 δ=.10 |
| `context_gate.py` | SC-6 (§8.5) | gate table on canonical modes |
| `competitive_recall.py` | SC-6 (§8.4/§8.6) | softmax, effective score, top-3 cap |
| `stm.py` | SC-1 (§3) | buffer eviction + promotion |
| `memory_store.py` | SC-2..SC-5 | in-memory stores + `query_uwm` |
| `semantic_memory.py` | SC-3 (§5.3) | confidence + contradiction handling |
| `identity.py` | SC-4 (§6.3/6.4) | update threshold + belief update (immutable-safe) |
| `forgetting_engine.py` | SC-7 (§9) | decay sweep, agglomerative complete-linkage clustering, semantic extraction, triggers |
| `audit_trail.py` | SC-8 (§10) | SHA-256 hash chain + narrative link detection |
| `arbiter.py` | §11 | `memory_arbiter` (read) + `build_query_embedding` + MemoryPacket |
| `state_updater.py` | §12 | `state_updater` (write path) |
| `uwm_updater.py` | SC-5 | `merge_uwm_update` — pure, LLM-free profile/people/situations/psychological merge |
| `identity_seed.py` | SC-4 | `default_identity_beliefs()` — boot-time seed |

**Backend/store injection.** `Embedder`, `VectorIndex`, the FCE generalizer, the identity
belief-generator, and the episode extractor are all injectable; the memory store and audit trail
are passed in. Production wires the Ollama `nomic-embed-text` embedder + **ChromaDB**
(`infra/vector_store/`) + PostgreSQL (`infra/db/`) and the LLM-backed generalizer/extractor; the
defaults are dependency-free. This supersedes an earlier all-MiniLM/hnswlib target that appeared
in an intermediate doc revision — don't re-reconcile to SQLite/hnswlib; check `infra/` for what's
actually running.

**Reconciliations baked into the spec above:**
- Recall weights corrected to α=.40 β=.30 γ=.20 δ=.10 and τ default 0.7 (config was stale).
- Storage: PostgreSQL + ChromaDB is the current, live backend (superseding an intermediate SQLite + hnswlib revision).
- Context-gate modes reconciled to Layer 3's canonical taxonomy; `celebration` row added (§8.5).
- `required_contradictions` inline comment fixed (0.3 → 4, not 3) — the `ceil` formula is authoritative (§5.3).
- Immutable-policy enforcement reference corrected from "Safety Layer (Layer 9)" to Layer 11 (Safety Agent, which owns crisis) (§6.5).
- Selection is deterministic top-3 by effective score (§8.6); softmax/τ is provided for optional stochastic variation (§8.4).

**Test coverage.** 107+ unit tests in `tests/unit/` (`test_memory_embedding`, `test_memory_strength`,
`test_recall_scorer`, `test_context_gate`, `test_competitive_recall`, `test_stm_buffer`,
`test_semantic_memory`, `test_identity_memory`, `test_memory_store`, `test_forgetting_engine`,
`test_memory_audit`, `test_memory_arbiter`, `test_state_updater`, `test_uwm_updater`) cover the
§17.2 requirements plus the live-wiring behavior below: recall formula + components, softmax
temperature behavior, decay correctness, the full gate table, consolidation (3 similar episodes →
semantic memory), hash-chain integrity + tamper detection, cross-session link detection, the
confabulation guard, contradiction-driven belief/semantic updates, and the UWM/identity round
trips through real serde and the real `ConversationOrchestrator`.

**SC-6 — Recall Scoring Engine: live, with one corrected input.** Recall's emotional component
used to receive a hardcoded neutral vector every turn (`api/assembly.py` passed
`EmotionVector(0,0,"neutral")` regardless of actual user state), which — given
`emotional_component`'s distance formula — systematically favored neutral-toned memories,
backwards from the mood-congruent-recall design intent (§18.3, and the CLAUDE.md invariant on
mood-congruent recall). Recall runs *before* Layer 3 classification by design (§11.2), so there
is no `EmotionClassification` available yet at that point; `_emotion_from_input_packet` now
derives a proxy from Layer 1's `composite_emotional_prior` instead. Verified by constructing two
identical-embedding memories differing only in `emotion_vector` and confirming recall ordering
flips between a high- and low-vulnerability input packet.

**SC-1 — Short-Term Memory Buffer: live and genuinely accumulating.** `infra/stm_store.py::
InProcessSTMStore` is a thread-safe, LRU-bounded (200 sessions) in-process `{session_key:
buffer}` map, satisfying §3.1's "ephemeral, RAM-only" requirement for this codebase's
single-process, single-user deployment (a restart, or LRU eviction of a very old session, wipes
it — correct per spec, not a bug). `api/state.py::make_state_update_writer` calls `stm.add_turn`
for both the user's message and Nova's response each turn. Promotion is checked **on arrival**,
not on eviction: each incoming user turn is checked against `stm.should_promote` (high arousal, a
life-event keyword, or an explicit `importance_flag`) immediately — real sessions are a handful
to a few dozen turns, nowhere near the 100-turn/30,000-char window (§3.2, raised from 40/12,000
for in-session coherence headroom now that promotion, not every-turn persistence, determines
long-term memory), so eviction-time checking would essentially never fire; it was removed as dead
code rather than kept as an unreachable second check. Only `role == "user"` turns are eligible —
Nova's own reply text can incidentally contain a life-event keyword and must never be recorded as
something the user said. Batching multiple promotable turns into one multi-turn-synthesized
episode (§3.1's "no multi-turn synthesis") is deliberately not done, since per-turn arrival
checking leaves essentially never more than one promotable turn to batch. Ordinary,
non-significant conversation is still never persisted as an episode by design — only turns that
trigger promotion become long-term memories; this is intentional lossiness for ordinary
conversation, not a bug. **Real gap still open:** accumulating `stm.turns` across requests has no
live consumer that reads it back into a prompt — `assembly.py::plan` still builds each turn's
prompt from only `ctx.message` + `recalled_memories`, so in-session "what did I say 3 messages
ago" recall is not yet live; wiring `stm.turns` into prompt construction is unstarted work.

**SC-2 — Episodic Memory Store: live with real LLM summarization.** `_summarize_promoted_turn`
(`api/state.py`) prompts the injected `system1` client for a short third-person summary of each
promoted turn, with the same best-effort fallback shape as `background/memory_consolidation_job
.py`'s `_generalize` (no client, or any exception, falls back to plain truncation, never blocks
the write path) — replacing an earlier `message[:2000]` truncation stub that ran on every turn
regardless of significance. Each created episode also carries the turn's real `emotion_vector`
(previously always the empty default), which also benefits Layer 10's `_episode_valence`-derived
emotional records. The same call additionally extracts up to 5 named entities
(`infra/llm/json_extract.extract_json`, same fallback contract — a parse failure or missing
client yields `entities: []`, not a blocking failure) into `EpisodicMemory.entity_refs`, which is
what makes narrative-chain linking (below) arithmetically possible.

**SC-2 — Narrative-chain linking: live end-to-end.** `detect_narrative_links` now has a real
caller and store. New `narrative_chain` table (`infra/db/models/memory.py`) +
`PostgresMemoryStore.save_narrative_chain`/`active_narrative_chains` (JSONB round-trip, same
pattern as `save_identity`/`save_uwm`; "active" means not `ChainStatus.ARCHIVED` — a `RESOLVED`
chain stays visible since nothing currently archives one). `api/state.py::_link_narrative_chains`
runs from the same closure that creates promoted episodes: for each newly-promoted episode it
loads the user's active chains, hydrates each chain's last episode, and calls
`detect_narrative_links` — a match appends to that chain, no match seeds a new one, best-effort
(a linking failure never loses the already-saved episode). Linking was arithmetically impossible
before the SC-2 entity-extraction fix above: the formula is `link_score = 0.6·semantic_similarity
+ 0.4·entity_overlap` against a `0.65` threshold (§10.3), and with `entity_refs` always `[]`,
`entity_overlap` was always `0`, capping the achievable score at `0.6` — below threshold even at
perfect semantic similarity. **Deliberately not done — reading chains back into generation.**
`MemoryPacket.active_narrative_chains` exists as a `memory_arbiter` parameter, but nothing in
`api/assembly.py::recall` forwards it past the hook's `list[memory]`-only return contract, and
nothing downstream would consume it if it did (matching Layer 4's own finding that most richer
context objects have no real prompt-building consumer yet).

**SC-5 — User World Model: live for `profile` + `relationship_graph` + `life_context` +
`psychological_model`; `communication_model` deliberately excluded.** Write path:
`uwm_updater.py::merge_uwm_update(uwm_or_none, user_id, extracted, now)` is pure, LLM-free merge
logic — profile fields set only when the extracted delta has a value (never blanked by a silent
turn), people matched case-insensitively by name (repeat mentions bump `mention_count`/
`last_mentioned_at` and merge traits rather than duplicating nodes), situations/stressors
deduplicated by description; it creates the first `UserWorldModel` row the first time there's
anything to persist and returns `None` (persisting nothing) on any silent turn — critical because
an earlier version only returned `None` when no row existed yet, so every ordinary turn *after*
the first real signal produced a meaningless `UWM_UPDATED` entry on the user-visible,
integrity-checked audit chain (`GET /memory/audit`) forever; caught and fixed before it shipped.
`state_updater.py`'s step 3 takes an optional `uwm_updater_fn` (mirroring the `extractor_fn`
pattern for episodes; without one, behavior is the original version-only bump — purely additive).
`api/state.py::make_state_update_writer` supplies the real closure: `_extract_uwm_signals` (a
per-turn LLM call, JSON-structured) → `merge_uwm_update`, run every turn (not promotion-gated,
since profile/relationship facts can surface in any ordinary message). Read path:
`api/assembly.py::build_persona` calls `uwm_provider` (`api/state.py::make_uwm_provider`) and
folds a plain-language `_uwm_directive` — known profile facts, top 3 people by mention count, up
to 2 active life situations — onto `PersonaPacket.persona_instruction`, reaching
`build_planner_prompt` through the real orchestrator (no raw scores, no structure dumped
verbatim, per this file's own invariant). `communication_model` is explicitly kept out of the UWM
write/read path: `backend/layer4_persona/style_learning.py` already owns communication style
live (EMA-updated, reaches `build_persona`'s directive), and building a second UWM-based version
of the same signal would fork it — a pattern CLAUDE.md already flags as a standing risk from the
original audit, avoided here rather than left for a future reconciliation. `psychological_model`
(attachment_signals, emotional_regulation_style, preferred_support_style, self_efficacy_signals,
identity_conflict_signals, known_triggers) was initially deferred as higher-stakes
amateur-psychological-profiling risk, then built after the user was asked explicitly and chose to
proceed: folded into the same `_extract_uwm_signals` call as a fourth JSON key
(`"psychological"`, same "only what this message actually states or clearly implies" evidentiary
bar as the other three keys), merged by `uwm_updater.py::_merge_psychological`
(dedup + `model_confidence` toward 1.0, capped at 10 contributing turns), and stays on-device only
structurally — `sync_coordinator.py` has no knowledge of the UWM store at all.
`PsychologicalModel.known_triggers` (`list[TriggerPattern]`) was checked against the bare-`list`
serde bug that previously bit Layers 7/9/10/13 and confirmed already correctly parametrized (real
round trip proven, not just an annotation read). **Not yet done:** nothing in
`build_persona`/generation reads `psychological_model` back out — this closes the write side only,
matching this pass's pattern of closing write paths before read paths land;
`persona_resolver.resolve_persona_state` already accepts the param, unused live.

**SC-4 — Identity Memory: live — seeded at boot, contradiction-checked every turn, read into the
prompt.** A doc-level gap had to be resolved first: the original §6.4 pseudocode for
`detect_identity_contradiction`/`apply_identity_update` doesn't typecheck (it sums `.strength`
over `evidence_against: list[str]`, which has no such field) — resolved by promoting
`evidence_against` to `list[IdentityEvidence]` (`summary`, `strength`, `session_id`,
`recorded_at`) and making `apply_identity_update`'s `prior_against_strength` auto-compute from it
when not explicitly overridden, which is what makes §6.3's multi-session evidence accumulation
("central beliefs require strong, repeated evidence") actually work across turns; on an actual
update `evidence_against` resets to `[]`. Contradiction detection
(`identity.py::detect_identity_contradictions`) sends the LLM the full list of non-immutable
belief statements in **one combined call** per turn — chosen over per-belief calls (no accuracy
benefit at this app's single-user scale) and an embedding-similarity pre-filter (risks discarding
a real contradiction phrased in unrelated-looking words, a false negative in exactly the case this
feature exists to catch); scores below `_CONTRADICTION_FLOOR = 0.15` are dropped as LLM noise, and
immutable beliefs are excluded from the prompt entirely, with `_identity_directive` and
`make_identity_writer` both re-filtering defensively as well. Seeding:
`identity_seed.py::default_identity_beliefs()` returns the 5 immutable safety policies from §6.5
plus a small starting personality, seeded idempotently at `build_app_state` boot rather than in a
separate script (this app has exactly one deployer); centralities deliberately sit well below the
immutable floor so genuine repeated disagreement can change them, though Layer 11's independent
hard-coded path is what actually enforces the immutable policies (§6.5) — this store adds no new
enforcement. Write: `api/state.py::make_identity_writer` runs post-turn, detects contradictions,
and for anything flagged calls `apply_identity_update` and persists the result. A real bug was
caught before shipping: `apply_identity_update`'s `generate_fn` defaulted to an offline
placeholder (`f"[revised] {belief.statement}"`), and the first writer version called it with no
override — a real threshold-crossing update would have persisted the literal string
`"[revised] Nova is direct rather than evasive..."` as Nova's actual belief, compounding a new
`"[revised] "` prefix on every subsequent update. Fixed two ways: `api/state.py
::_revise_belief_statement` is a real second LLM call wired as the generator, and
`apply_identity_update` itself now treats a `generate_fn` returning empty/unchanged text as "no
rewrite this turn" (evidence still recorded, no `BeliefUpdateEvent`, statement untouched) rather
than a real update — defense in depth so a future caller forgetting a real generator degrades to
"belief doesn't update," never to persisting corrupted text. Seeded
personality/relational/core-value centralities were also raised (0.5–0.85 → 0.7–0.9) since an LLM
asked for a 0–1 contradiction score readily emits 0.8–0.9 for ordinary disagreement, and §6.3's
"strong, repeated evidence" bar only holds in practice if the threshold accounts for that. Read:
`api/state.py::make_identity_provider` selects the top-3 highest-centrality non-immutable beliefs
(not the whole table, to avoid compounding prompt bloat), and `build_persona` folds them into
`persona_instruction` as plain sentences via `_identity_directive`.

**Cost note (applies across SC-2/SC-4/SC-5 above).** `session_writer`'s post-turn chain makes up
to 5 sequential LLM calls beyond Layer 3's classifier call and (on a promoted turn) episodic
summarization: goal extraction, Layer 5's person-mention extraction, UWM signal extraction
(profile/situations/stressors/psychological), identity contradiction detection, and — only when a
contradiction crosses threshold — the belief-rewrite call. `POST /chat` is synchronous and
`run_turn` awaits the full write path, so request latency includes all of them — acceptable for
this app (local, single-user, `system1` is the fast local model throughout), but worth knowing
before assuming `/chat` latency is dominated by generation alone.

**File-length cleanup + dead-schema pruning (2026-08-10).** `schemas.py` (598 lines) split into
a `schemas/` package by sub-component (`enums.py`, `emotion.py`, `stm.py`, `episodic.py`,
`semantic.py`, `identity.py`, `uwm.py`, `audit_narrative.py`, `fce.py`, `recall.py`), all under
the 200-line cap, with `__init__.py` re-exporting everything so every existing
`from backend.layer2_memory.schemas import X` import kept working unchanged. `api/routes/
memory.py` (298 lines) was similarly split by layer ownership: the genuinely Layer-2 routes
(`GET /memory/audit`, `/integrity`, `/search`, `/{id}`) stayed; the Layer-12 routes (`DELETE
/memory/{id}`, `/audit/full`, `/audit/query`, `POST /{id}/correct`) and their six duck-type
adapter classes moved to new `api/routes/privacy.py` + `api/routes/privacy_adapters.py` — see
`docs/layer-12-architecture.md` for the updated file references. Re-audit of the UWM schema
found `RelationshipEdge`/`SentimentPoint` and `RecurringTheme` fully defined but never
constructed by `uwm_updater.py` and never read anywhere, unlike `PersonNode`/`LifeSituation`/
`Stressor` in the same package (which are genuinely populated, just with a few individually
unset fields — left alone, matching Layer 1's precedent of not touching partially-set-but-live
classes). `RelationshipEdge` duplicated Layer 5's already-partially-live `SocialEdge`
(tie_strength, shared_contexts, sentiment trend) — deleted rather than wired, to avoid forking
relationship-edge data the way `communication_model`'s exclusion already avoided forking
communication-style data. Full test suite (1588 passed, 1 skipped) verified before and after.

## 20. Decision Log

- **2026-08-04 (Phase 2 polish pass):** Audited every module for a real caller; found 5 of 8
  sub-components with no live production caller at all (STM real accumulation, episodic real
  extraction, narrative-chain linking, UWM, Identity Memory). Fixed the recall emotional-component
  bug (hardcoded neutral vector defeated mood-congruent recall) and stale SQLite+hnswlib/all-MiniLM
  doc references. Logged the 5 unwired sub-components for follow-up passes.
- **2026-08-05 (Phase 2 follow-up — STM + episodic):** Made STM a real accumulating,
  LRU-bounded, cross-request buffer (`InProcessSTMStore`); moved promotion checking to
  turn-arrival (eviction-time checking was dead code given real session sizes); raised
  `max_turns`/`char_limit` 40/12,000 → 100/30,000; replaced the `message[:2000]` truncation stub
  with real LLM summarization for promoted-turn episodes. Left `stm.turns` prompt-reading (true
  in-session recall) and multi-turn episode batching as open follow-ups.
- **2026-08-05 (Phase 2 follow-up — narrative-chain linking):** Wired `detect_narrative_links`
  into the write path via a new `narrative_chain` table + `_link_narrative_chains`. Found and
  fixed a blocking bug: `entity_refs` was always `[]`, capping the link score below threshold even
  at perfect similarity — fixed by extracting entities in the same per-turn summarization call.
  Left reading chains back into generation unwired (no consumer exists downstream yet).
- **2026-08-05 (Phase 2 follow-up — User World Model):** Wired `profile`/`relationship_graph`/
  `life_context` write (`merge_uwm_update`) and read (`uwm_provider` → `build_persona`) paths.
  Caught and fixed a bug pre-ship: an earlier merge version produced a meaningless `UWM_UPDATED`
  audit-chain entry on every turn after the first real signal. Deliberately excluded
  `communication_model` (already owned live by Layer 4's `style_learning.py`, avoiding a fork) and
  deferred `psychological_model` as a higher-stakes decision pending user sign-off.
- **2026-08-05 (Phase 2 follow-up — Identity Memory):** Fixed a doc-level schema gap
  (`evidence_against` promoted to `list[IdentityEvidence]` so multi-session evidence accumulation
  is actually computable). Wired boot-time seeding, one-combined-call contradiction detection, and
  read-into-prompt. Caught and fixed a bug pre-ship: the belief-rewrite generator defaulted to an
  offline placeholder string that would have been persisted as Nova's literal belief; wired a real
  second LLM call and added a fail-safe (no rewrite rather than corrupted text). Raised seeded
  centralities so single strongly-worded disagreements can't overwrite a trait outright.
- **2026-08-09 (follow-up, product decision confirmed with the user):** Built
  `psychological_model` extraction (previously deferred as higher-stakes) after explicit user
  sign-off — folded into the existing UWM extraction call as a fourth JSON key, with the same
  strict evidentiary bar as the other three. Verified `known_triggers`' nested-dataclass field
  doesn't hit the bare-`list` serde bug that affected other layers. Closed the write side only;
  the read side (generation reading `psychological_model` back out) remains unwired pending a
  concrete reason to change generation behavior based on it.
- **2026-08-10 (simplification pass):** Split `schemas.py` and `api/routes/memory.py` under the
  200-line file cap (see §19 for the full module map). Deleted `RelationshipEdge`/
  `SentimentPoint` (duplicated Layer 5's live `SocialEdge`) and `RecurringTheme` (no producer or
  consumer anywhere) from the UWM schema and this doc's §7.4/§7.5 spec tables, after confirming
  with the user this was genuine cross-layer duplication rather than an unwired-but-intended
  field — the same judgment call as Layer 1's `longest_historical_gap_days` decision, resolved
  the other way here because a live duplicate already exists in Layer 5.

---

*This document specifies Layer 2 completely. All eight sub-components have full schemas, all algorithms are specified with exact logic, all gaps from the original design (User World Model schema, contradiction detection mechanism, clustering algorithm, audit trail, cross-session linking) are resolved. Live wiring status as of the most recent audit pass is tracked in §19 and `docs/POLISH_BACKLOG.md`; no behavior of Layer 2 requires assumptions or inferences from other documents.*
