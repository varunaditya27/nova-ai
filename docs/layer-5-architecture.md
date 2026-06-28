# Layer 5 — Social Intelligence & Coaching
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

If Layer 4 governs *who Nova is and what it says*, Layer 5 governs **what Nova understands about the people in the user's life and the social dynamics between them**. This is the layer that makes Nova a genuinely socially intelligent companion — not just emotionally attentive to the user, but capable of reasoning about the user's relationships, social patterns, interpersonal conflicts, communication habits, and the quality of their support network.

The distinction from previous layers is precise: Layer 3 reads the emotional state of the current message. Layer 4 crafts an emotionally appropriate response. Layer 5 operates at a longer timescale — it accumulates social knowledge *across sessions*, builds a model of the user's relational world, and uses that model to provide coaching, perspective, and pattern recognition that the user cannot always give themselves.

Layer 5 is not a therapy layer and is not a crisis layer. It is a **social intelligence layer** — the equivalent of a trusted friend who has been paying close attention to the people and situations you keep bringing up, and who can say: *"This is the third time you've described your friend like that. Have you noticed that pattern?"* or *"The way you're describing this conflict sounds a lot like what happened with your roommate in March."*

The central claim of this layer: **social context is the missing dimension in every existing AI companion system**. Emotional support without social context is inherently shallow. A friend who remembers your feelings but doesn't know your relationships cannot offer real perspective.

Layer 5 contains **five sub-components**:

- **SC-1: Social Graph Manager** — structured model of the user's relationships and social network
- **SC-2: Interpersonal Event Tracker** — detects, classifies, and stores social events (conflicts, reconnections, milestones, drift)
- **SC-3: Social Pattern Recognizer** — identifies recurring dynamics and behavioral patterns across the user's relationships
- **SC-4: Coaching Opportunity Detector** — determines when and how to offer social perspective or coaching
- **SC-5: Social Coaching Response Modifier** — modifies the Layer 4 response to integrate social intelligence without overwhelming the primary response

All five sub-components run in **parallel with Layer 4** when the conversation domain is `relationships` or `social`, and **post-response** (as background processing) for all other domains. The key distinction: SC-1 through SC-3 are always updating. SC-4 and SC-5 only inject into the active response pipeline when a coaching opportunity is detected and timing conditions are met.

---

## 2. Architecture Overview

```
Inputs consumed by Layer 5:
 ├── FinalResponsePacket (Layer 4)
 │     ├── final_text
 │     ├── topic_domain
 │     └── intent_served
 ├── EmotionIntentPacket (Layer 3)
 │     ├── primary_emotion
 │     ├── intent (with topic_domain)
 │     ├── conversation_mode
 │     └── background_state
 ├── MemoryPacket (Layer 2)
 │     ├── uwm_context (relationship_graph, social_context)
 │     ├── recalled_memories
 │     └── stm_turns
 └── TemporalContextObject (Layer 1)
       └── circadian_band, session_gap_category

          │
          ├────────────────────────────────────┐
          │                                    │ (parallel processing)
          ▼                                    ▼
┌──────────────────────────┐        ┌──────────────────────────────┐
│ SC-1: Social Graph       │        │ SC-2: Interpersonal Event    │
│       Manager            │        │       Tracker                │
│ (relationship model)     │        │ (detect + classify events)   │
└──────────────────────────┘        └──────────────────────────────┘
          │                                    │
          └────────────────┬───────────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │ SC-3: Social Pattern       │
              │       Recognizer           │
              │ (cross-session dynamics)   │
              └────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │ SC-4: Coaching Opportunity │
              │       Detector             │
              │ (when + how to coach)      │
              └────────────────────────────┘
                           │
              ┌────────────┴────────────────┐
              │ coaching_opportunity: None  │ → pass through (Layer 4 response unchanged)
              │ coaching_opportunity: Some  │ → SC-5
              └─────────────────────────────┘
                           │ (if Some)
                           ▼
              ┌────────────────────────────┐
              │ SC-5: Social Coaching      │
              │       Response Modifier    │
              │ (augment Layer 4 response) │
              └────────────────────────────┘
                           │
                           ▼
                  SocialIntelligencePacket
                  (passed to Layer 6, Layer 7, and Layer 9)
```

**Execution model:**
- SC-1 + SC-2 run in parallel, both triggered on every message
- SC-3 runs after SC-1 + SC-2 complete; uses their outputs
- SC-4 runs after SC-3; takes < 10ms
- SC-5 runs only if SC-4 detects an opportunity; it modifies the Layer 4 FinalResponsePacket before Layer 9 delivers it
- Total path when no coaching opportunity: SC-1–4 are background processes; Layer 4 response passes through unchanged
- Total path when coaching opportunity: SC-5 adds < 200ms to response path (one lightweight LLM call or template-based injection)

---

## 3. Sub-Component 1 — Social Graph Manager

### 3.1 Purpose

The Social Graph Manager maintains a structured, persistent model of every named person or entity in the user's social world — built exclusively from what the user has said across sessions. It does not infer relationships not mentioned. It does not speculate about third parties. It stores what the user has described, with confidence scores that reflect how consistently those descriptions have held.

The Social Graph is the structured substrate that makes all social intelligence possible. Without it, SC-2 through SC-5 have no relational context — they cannot reason about *who* is involved in a conflict, whether a pattern of behavior is consistent with a person's history, or whether a relationship is deteriorating.

### 3.2 Social Graph Schema

```python
class SocialGraph:
    user_id: str
    nodes: dict[str, SocialNode]       # key = person_id (stable internal ID)
    edges: dict[tuple, SocialEdge]     # key = (person_id_a, person_id_b)
    last_updated: datetime
    version: int                        # increments on every structural update

class SocialNode:
    person_id: str                      # stable internal UUID; never the real name
    display_name: str                   # what user calls them ("my sister", "Riya", "my manager")
    name_aliases: list[str]             # all names/references used for this person
    relationship_type: Literal[
        "family_immediate",             # parent, sibling, partner
        "family_extended",              # grandparent, cousin, aunt/uncle
        "romantic_partner",
        "close_friend",
        "friend",
        "acquaintance",
        "colleague",
        "manager",
        "mentor",
        "peer_academic",
        "peer_professional",
        "authority_figure",             # professor, doctor, landlord
        "rival",
        "ex",
        "online_friend",
        "unknown"                       # mentioned but type unclear
    ]
    relationship_subtype: Optional[str] # e.g., "college friend", "childhood friend", "lab partner"

    # Emotional valence of relationship (how user feels about this person overall)
    relationship_valence: float         # –1.0 to +1.0; updated from session evidence
    valence_confidence: float           # 0–1; low for rarely mentioned people
    valence_trend: float                # slope; positive = improving, negative = worsening

    # Interaction frequency (as reported by user)
    interaction_frequency: Literal["daily", "weekly", "monthly", "rarely", "estranged", "unknown"]

    # Stability of the relationship in the user's narrative
    narrative_stability: float          # 0–1; high = consistently described; low = contradictory descriptions

    # Conflict history
    active_conflict: bool
    conflict_count: int                 # number of conflicts mentioned across sessions
    conflict_topics: list[str]          # recurring conflict themes (extracted, not raw text)

    # Emotional support role (does this person support the user emotionally?)
    is_support_source: bool
    support_quality: Optional[float]   # 0–1; how well they support user (per user's reports)

    # First mentioned
    first_mentioned: datetime
    last_mentioned: datetime
    mention_count: int

    # Metadata
    data_source: str                    # "user_stated" always; never inferred
    confidence: float                   # overall confidence in this node's accuracy
```

```python
class SocialEdge:
    person_id_a: str                    # one is always the user; the other is the person
    person_id_b: str
    relationship_type: str              # from SocialNode.relationship_type
    tie_strength: float                 # 0–1; how important this person is to the user
    tie_strength_trend: float           # improving or declining
    last_interaction_reported: Optional[datetime]
    shared_contexts: list[str]          # domains where this relationship is active ("academic", "home", "work")
    co_mentions: list[str]              # other person_ids frequently mentioned alongside this person
```

### 3.3 Social Graph Update Logic

The Social Graph is updated by the **Layer 2 State Updater** after each session, using social events detected by SC-2. The update logic follows three rules:

**Rule 1 — Node creation:** A new node is created when a previously unmentioned person is named or clearly referenced and has been mentioned at least twice in the session (to avoid ephemeral mentions creating noise).

**Rule 2 — Node update:** Existing nodes are updated when the user provides new information about the person. Valence updates follow a rolling weighted average (recent sessions weighted more). Conflict flags are set/cleared based on SC-2 event detection.

**Rule 3 — Node confidence decay:** A person not mentioned for 90+ days has their `confidence` reduced by 0.05 per additional 30 days. This reflects that the user's relationship context may have changed without Nova knowing. It does not delete the node — it marks it as stale so that references include appropriate epistemic humility ("last time you mentioned Riya, it seemed like things were tense — has that changed?").

### 3.4 Entity Resolution

The most technically challenging aspect of the Social Graph is **entity resolution** — recognizing that "my sister", "Priya", and "P." all refer to the same person across different sessions.

```python
def resolve_entity(
    mention: str,
    context: str,
    existing_nodes: list[SocialNode]
) -> tuple[Optional[str], float]:
    """
    Returns (person_id, confidence) if a match is found.
    Returns (None, 0.0) if this is a new entity.
    """
    candidates = []
    for node in existing_nodes:
        # Check name alias match
        if mention.lower() in [a.lower() for a in node.name_aliases]:
            candidates.append((node.person_id, 0.95))
            continue

        # Check relationship type match from context
        inferred_rel = infer_relationship_from_context(mention, context)
        if inferred_rel and inferred_rel == node.relationship_type:
            candidates.append((node.person_id, 0.70))
            continue

        # Semantic similarity of mention context to node descriptions
        mention_embedding = embed(mention + " " + context)
        node_embedding = embed(node.display_name + " " + node.relationship_subtype or "")
        sim = cosine_similarity(mention_embedding, node_embedding)
        if sim > 0.82:
            candidates.append((node.person_id, sim))

    if not candidates:
        return None, 0.0

    best_match = max(candidates, key=lambda x: x[1])
    if best_match[1] < 0.65:
        return None, 0.0    # confidence too low; treat as new entity

    return best_match
```

When entity resolution confidence is between 0.65 and 0.80, the system does not act on the match silently — it stores it as a **tentative match** and confirms it over subsequent sessions. Only matches above 0.80 update the node directly.

---

## 4. Sub-Component 2 — Interpersonal Event Tracker

### 4.1 Purpose

The Interpersonal Event Tracker detects, classifies, and stores **social events** — meaningful moments in the user's relational world that have been described in conversation. A social event is not just a mention of a person; it is a situation involving a person that has a type, a valence, and a trajectory.

Events are the raw material of social pattern recognition. Without a structured log of events, SC-3 has nothing to analyze.

### 4.2 Social Event Taxonomy

```python
class SocialEventType(str, Enum):
    # Conflict events
    CONFLICT_ONSET           = "conflict_onset"          # new conflict beginning
    CONFLICT_ESCALATION      = "conflict_escalation"     # existing conflict worsening
    CONFLICT_DEESCALATION    = "conflict_deescalation"   # conflict improving
    CONFLICT_RESOLUTION      = "conflict_resolution"     # conflict explicitly resolved
    CONFLICT_DORMANT         = "conflict_dormant"        # conflict stopped being mentioned (ambiguous)

    # Connection events
    RECONNECTION             = "reconnection"            # re-engaging after distance
    DEEPENING                = "deepening"               # relationship becoming closer
    DRIFT                    = "drift"                   # relationship becoming more distant
    RUPTURE                  = "rupture"                 # significant relationship break
    REPAIR                   = "repair"                  # relationship repaired after rupture

    # Milestone events
    LIFE_MILESTONE_SHARED    = "life_milestone_shared"   # other person's milestone (graduation, marriage, birth)
    ACHIEVEMENT_SHARED       = "achievement_shared"      # other person's achievement
    LOSS_SHARED              = "loss_shared"             # other person's loss (job, relationship, bereavement)

    # Behavioral events
    BOUNDARY_VIOLATION       = "boundary_violation"      # other person crossed a boundary
    SUPPORT_RECEIVED         = "support_received"        # other person supported user
    SUPPORT_WITHHELD         = "support_withheld"        # user expected support; didn't receive it
    BETRAYAL                 = "betrayal"                # trust broken by other person
    POSITIVE_SURPRISE        = "positive_surprise"       # unexpectedly positive behavior from other person

    # User behavior events (about the user's own social actions)
    USER_SET_BOUNDARY        = "user_set_boundary"       # user asserted a limit
    USER_AVOIDED_CONFLICT    = "user_avoided_conflict"   # user chose not to address something
    USER_REACHED_OUT         = "user_reached_out"        # user initiated contact or reconnection
    USER_WITHDREW            = "user_withdrew"           # user pulled back from relationship
```

### 4.3 Social Event Schema

```python
class SocialEvent:
    event_id: str                           # stable UUID
    session_id: str                         # session in which this was described
    person_id: str                          # who this event involves
    event_type: SocialEventType

    # Event description (never raw user text; always extracted summary)
    summary: str                            # 1–2 sentence neutral description
    user_perspective: str                   # what the user felt about it

    # Emotional valence of the event for the user
    event_valence: float                    # –1.0 to +1.0
    emotional_intensity: float             # 0–1

    # Temporal context
    event_timestamp: Optional[datetime]    # when the event occurred (if user stated)
    reported_timestamp: datetime           # when user reported it to Nova
    recency: Literal["current", "recent", "past", "distant_past"]  # relative label

    # Resolution status
    is_resolved: bool
    resolution_timestamp: Optional[datetime]
    resolution_summary: Optional[str]

    # Confidence
    extraction_confidence: float           # 0–1; how certain Nova is this event was described

    # Cross-references
    related_event_ids: list[str]           # prior events of same type with same person
    pattern_id: Optional[str]             # if part of a recognized pattern (from SC-3)
```

### 4.4 Event Detection Logic

Events are detected in two passes after each session:

**Pass 1 — Rule-based heuristic detection (fast, high precision for common events):**

```python
EVENT_DETECTION_RULES = [
    # Conflict onset
    {
        "patterns": [
            r"(fight|argument|argument|confrontation|fell out|blow up) with",
            r"(angry at|upset with|not talking to|avoiding)",
            r"(we had a|there was a) (fight|disagreement|argument)"
        ],
        "event_type": SocialEventType.CONFLICT_ONSET,
        "min_confidence": 0.80
    },
    # Support withheld
    {
        "patterns": [
            r"(didn't|didn't|did not) (support|help|show up|check in|respond)",
            r"(was not|wasn't|wasn't) there for me",
            r"(expected|thought) (they|he|she) would (but|and)"
        ],
        "event_type": SocialEventType.SUPPORT_WITHHELD,
        "min_confidence": 0.72
    },
    # Boundary violation
    {
        "patterns": [
            r"(crossed a line|overstepped|invaded|violated|went through)",
            r"(didn't respect|ignored) (my|the) (boundary|space|limit|request)",
            r"(pressured|forced|guilted|manipulated) me"
        ],
        "event_type": SocialEventType.BOUNDARY_VIOLATION,
        "min_confidence": 0.75
    },
    # Reconnection
    {
        "patterns": [
            r"(reached out|texted|called) (me|them|us) (after|again)",
            r"(we) (caught up|reconnected|talked again|met up)",
            r"(haven't talked|hadn't talked) (but|and) (they|we)"
        ],
        "event_type": SocialEventType.RECONNECTION,
        "min_confidence": 0.78
    },
    # User set boundary
    {
        "patterns": [
            r"(told|said to) (them|him|her) (that|how|why) (I|it|this)",
            r"(set|put) (a |my )?(boundary|limit|rule)",
            r"(made it clear|was clear) (that|about)"
        ],
        "event_type": SocialEventType.USER_SET_BOUNDARY,
        "min_confidence": 0.70
    }
]
```

**Pass 2 — LLM-based event extraction (for ambiguous or complex events):**

When the rule-based pass produces low confidence or no match, a lightweight LLM call extracts structured events from the session summary. This is a **post-session background process** — it does not run on the live response path:

```
SYSTEM:
You are a social event extractor. Given a conversation summary, extract structured
social events. Only extract events that are explicitly described — do not infer
or speculate. Output valid JSON only.

CONVERSATION SUMMARY:
{session_summary}

KNOWN PEOPLE IN USER'S SOCIAL GRAPH:
{social_graph_brief}

OUTPUT:
{
  "events": [
    {
      "person_reference": "<how user referred to them>",
      "event_type": "<from taxonomy>",
      "summary": "<1–2 sentence neutral description>",
      "user_perspective": "<how user felt>",
      "event_valence": <float>,
      "emotional_intensity": <float>,
      "recency": "<current|recent|past|distant_past>",
      "is_resolved": <bool>,
      "extraction_confidence": <float>
    }
  ]
}
```

### 4.5 Event Persistence and Retrieval

All detected events are stored in the Layer 2 episodic memory store with a `memory_type = "social_event"` tag. They are retrievable by:
- `person_id` — all events involving a specific person
- `event_type` — all events of a specific type (e.g., all conflicts)
- `date range` — events within a time window
- `pattern_id` — all events belonging to a recognized pattern

Events are not deleted unless the Social Graph node is explicitly removed by the user. They decay in retrieval salience (via the Layer 2 decay function) but are archived, not deleted — because pattern recognition over long time horizons requires historical data.

---

## 5. Sub-Component 3 — Social Pattern Recognizer

### 5.1 Purpose

The Social Pattern Recognizer is the analytical layer of Layer 5. It looks across the accumulated event history and social graph to identify **recurring dynamics** — patterns of behavior that repeat across time, across relationships, or within a specific relationship. These patterns are what distinguish genuine social intelligence from simple event logging.

Patterns operate at three levels:
1. **Intra-relationship patterns** — recurring dynamics within a single relationship (e.g., the same conflict topic recurring with the same person every few months)
2. **Cross-relationship patterns** — the user exhibiting the same behavior across multiple different relationships (e.g., consistently avoiding conflict across all close relationships)
3. **Temporal patterns** — the user's relational behavior changing over time in a consistent direction (e.g., progressively withdrawing from all social contact)

### 5.2 Pattern Taxonomy

```python
class SocialPatternType(str, Enum):
    # Intra-relationship
    RECURRING_CONFLICT_TOPIC         = "recurring_conflict_topic"
    RECURRING_SUPPORT_FAILURE        = "recurring_support_failure"       # person repeatedly fails to support
    RECURRING_POSITIVE_REINFORCEMENT = "recurring_positive_reinforcement" # person consistently positive
    RELATIONSHIP_CYCLING             = "relationship_cycling"            # drift and reconnect repeatedly
    ESCALATING_TENSION               = "escalating_tension"              # conflict intensity increasing over time
    STABILIZING_RELATIONSHIP         = "stabilizing_relationship"        # improving trend

    # Cross-relationship (user behavior patterns)
    CONFLICT_AVOIDANCE_PATTERN       = "conflict_avoidance_pattern"      # user avoids conflict broadly
    PEOPLE_PLEASING_PATTERN          = "people_pleasing_pattern"         # user subordinates own needs
    BOUNDARY_DIFFICULTY_PATTERN      = "boundary_difficulty_pattern"     # user has consistent boundary issues
    SOCIAL_WITHDRAWAL_PATTERN        = "social_withdrawal_pattern"       # user progressively more isolated
    DEPENDENCY_PATTERN               = "dependency_pattern"              # user over-relies on one person
    HEALTHY_RELATIONSHIP_PATTERN     = "healthy_relationship_pattern"    # user maintains consistently healthy rels

    # Temporal
    NETWORK_SHRINKAGE                = "network_shrinkage"               # social network becoming smaller over time
    NETWORK_GROWTH                   = "network_growth"                  # social network expanding
    SUPPORT_NETWORK_EROSION          = "support_network_erosion"         # support sources decreasing
    INCREASED_SOCIAL_ENGAGEMENT      = "increased_social_engagement"     # user more socially active
```

### 5.3 Pattern Schema

```python
class SocialPattern:
    pattern_id: str
    pattern_type: SocialPatternType

    # What pattern involves
    scope: Literal["intra_relationship", "cross_relationship", "temporal"]
    person_ids_involved: list[str]      # empty for temporal patterns

    # Evidence
    supporting_event_ids: list[str]     # event IDs that constitute the evidence
    event_count: int                    # how many events support this pattern
    first_observed: datetime
    last_observed: datetime
    observation_span_days: int

    # Pattern description (for use in coaching)
    plain_language_description: str     # "You've described a conflict with Riya about shared space 4 times over 6 months"
    coaching_hook: str                  # the specific observation that could open a conversation

    # Confidence and strength
    pattern_confidence: float           # 0–1; how certain this is a real pattern vs. noise
    pattern_strength: float             # 0–1; how pronounced the pattern is

    # Status
    is_active: bool                     # True = still occurring; False = may have resolved
    last_activation: datetime
    has_been_surfaced: bool             # True = Nova has mentioned this to user before
    surface_count: int                  # how many times surfaced
    user_acknowledged: bool             # True = user engaged with this observation
```

### 5.4 Pattern Detection Algorithm

Patterns are detected by the Social Pattern Recognizer in a **background batch process** triggered every 5 sessions, not per-message. This is a deliberate design decision: real patterns require longitudinal evidence. Detecting patterns per-message would produce false positives constantly.

```python
def detect_patterns(
    social_graph: SocialGraph,
    event_history: list[SocialEvent],
    min_events: int = 3,
    min_span_days: int = 30
) -> list[SocialPattern]:
    """
    Runs every 5 sessions. Returns all currently active patterns.
    """
    patterns = []

    # ── Intra-relationship patterns ──────────────────────────────────────────
    for person_id, node in social_graph.nodes.items():
        person_events = [e for e in event_history if e.person_id == person_id]

        # Recurring conflict topic detection
        conflict_events = [e for e in person_events
                          if e.event_type in [
                              SocialEventType.CONFLICT_ONSET,
                              SocialEventType.CONFLICT_ESCALATION
                          ]]
        if len(conflict_events) >= min_events:
            # Cluster conflicts by topic embedding
            topic_clusters = cluster_by_semantic_similarity(
                [e.summary for e in conflict_events],
                threshold=0.72
            )
            for cluster in topic_clusters:
                if len(cluster) >= 2:
                    span = (cluster[-1].reported_timestamp - cluster[0].reported_timestamp).days
                    if span >= min_span_days:
                        patterns.append(SocialPattern(
                            pattern_type=SocialPatternType.RECURRING_CONFLICT_TOPIC,
                            scope="intra_relationship",
                            person_ids_involved=[person_id],
                            supporting_event_ids=[e.event_id for e in cluster],
                            event_count=len(cluster),
                            first_observed=cluster[0].reported_timestamp,
                            last_observed=cluster[-1].reported_timestamp,
                            observation_span_days=span,
                            pattern_confidence=min(0.95, 0.5 + len(cluster) * 0.1),
                            pattern_strength=len(cluster) / 10.0,
                            plain_language_description=generate_pattern_description(
                                SocialPatternType.RECURRING_CONFLICT_TOPIC,
                                node.display_name, cluster
                            ),
                            ...
                        ))

        # Support failure pattern
        support_failure_events = [e for e in person_events
                                  if e.event_type == SocialEventType.SUPPORT_WITHHELD]
        if len(support_failure_events) >= 2:
            span = (support_failure_events[-1].reported_timestamp -
                    support_failure_events[0].reported_timestamp).days
            if span >= min_span_days:
                patterns.append(SocialPattern(
                    pattern_type=SocialPatternType.RECURRING_SUPPORT_FAILURE,
                    person_ids_involved=[person_id],
                    ...
                ))

    # ── Cross-relationship patterns ──────────────────────────────────────────

    # Conflict avoidance detection
    avoidance_events = [e for e in event_history
                       if e.event_type == SocialEventType.USER_AVOIDED_CONFLICT]
    unique_persons = len(set(e.person_id for e in avoidance_events))
    if len(avoidance_events) >= 3 and unique_persons >= 2:
        patterns.append(SocialPattern(
            pattern_type=SocialPatternType.CONFLICT_AVOIDANCE_PATTERN,
            scope="cross_relationship",
            person_ids_involved=list(set(e.person_id for e in avoidance_events)),
            supporting_event_ids=[e.event_id for e in avoidance_events],
            ...
        ))

    # Social withdrawal detection
    all_people_mention_counts = compute_mention_counts_by_window(event_history, window_days=30)
    if is_declining_trend(all_people_mention_counts, min_windows=3):
        patterns.append(SocialPattern(
            pattern_type=SocialPatternType.SOCIAL_WITHDRAWAL_PATTERN,
            scope="temporal",
            person_ids_involved=[],
            ...
        ))

    return [p for p in patterns if p.pattern_confidence >= 0.55]
```

---

## 6. Sub-Component 4 — Coaching Opportunity Detector

### 6.1 Purpose

The Coaching Opportunity Detector answers a single question: **given everything Layer 5 knows, is this the right moment to offer a social observation or gentle coaching?**

The word "coaching" here is used deliberately in the non-directive, non-prescriptive sense. Nova is not a therapist. It does not diagnose. It does not tell the user what to do. Coaching in this context means: offering a thoughtful observation, gently naming a pattern the user may not see, asking a question that creates perspective, or reflecting back what Nova has noticed over time.

Getting the timing wrong is worse than not coaching at all. An observation offered too early, in the wrong emotional state, or too frequently becomes intrusive, unwanted, and damaging to the relationship. The Coaching Opportunity Detector's job is to be conservative — to find the narrow window where coaching would be genuinely helpful and non-intrusive.

### 6.2 Coaching Types

```python
class CoachingType(str, Enum):
    PATTERN_REFLECTION      = "pattern_reflection"      # reflecting a recurring dynamic back to user
    PERSPECTIVE_OFFER       = "perspective_offer"       # offering a different angle on a situation
    RELATIONSHIP_CHECK_IN   = "relationship_check_in"   # noticing a person hasn't been mentioned
    GENTLE_REFRAME          = "gentle_reframe"          # user is catastrophizing; offer grounded frame
    STRENGTH_ACKNOWLEDGMENT = "strength_acknowledgment" # notice a positive behavior user is showing
    SUPPORT_NETWORK_NUDGE   = "support_network_nudge"   # notice user's support network is thin; suggest reaching out
    CONFLICT_NAVIGATION     = "conflict_navigation"     # user is in conflict; offer structured perspective
    BOUNDARY_SUPPORT        = "boundary_support"        # user is struggling with a boundary; validate + support
```

### 6.3 Opportunity Detection Schema

```python
class CoachingOpportunity:
    opportunity_detected: bool
    coaching_type: Optional[CoachingType]

    # Evidence basis
    triggering_pattern: Optional[SocialPattern]
    triggering_event: Optional[SocialEvent]
    triggering_person: Optional[str]       # person_id

    # Delivery parameters
    delivery_mode: Literal[
        "inline",               # add to current response (1–2 sentences)
        "as_question",          # frame as a gentle question at end of response
        "deferred",             # note for a future session; do not surface now
        "proactive_future"      # flag for Layer 6 proactive follow-up in a future session
    ]
    urgency: Literal["low", "medium", "high"]

    # The observation itself (plain language, ready for injection)
    observation_text: str                  # what Nova will say
    observation_framing: str               # how to introduce it ("I've been noticing..." / "Can I ask something?")

    # Constraints
    max_length_chars: int                  # how much space this can take in the response
    requires_explicit_consent: bool        # True = ask first before sharing observation
```

### 6.4 Detection Logic

The Coaching Opportunity Detector applies a **three-gate model**: the observation must pass all three gates to be surfaced in the current response.

**Gate 1 — Availability gate (is there something worth saying?):**

```python
def gate_1_availability(
    active_patterns: list[SocialPattern],
    recent_events: list[SocialEvent],
    social_graph: SocialGraph
) -> Optional[CoachingOpportunity]:
    """
    Returns the highest-priority observation available.
    Returns None if nothing is worth surfacing.
    """
    # Priority 1: Active pattern that hasn't been surfaced or was acknowledged
    unsurfaced_patterns = [p for p in active_patterns
                          if not p.has_been_surfaced and p.pattern_confidence >= 0.70]
    acknowledged_patterns = [p for p in active_patterns
                             if p.user_acknowledged and
                             (datetime.utcnow() - p.last_activation).days > 30]

    candidates = sorted(unsurfaced_patterns + acknowledged_patterns,
                        key=lambda p: p.pattern_strength, reverse=True)

    if candidates:
        best = candidates[0]
        return build_opportunity_from_pattern(best)

    # Priority 2: High-intensity unresolved conflict with known person
    active_conflicts = [e for e in recent_events
                       if e.event_type in [SocialEventType.CONFLICT_ONSET, SocialEventType.CONFLICT_ESCALATION]
                       and not e.is_resolved
                       and e.emotional_intensity > 0.6]
    if active_conflicts:
        return build_opportunity_from_conflict(active_conflicts[0], social_graph)

    # Priority 3: Support network erosion (no support sources mentioned in 30+ days)
    support_sources = [n for n in social_graph.nodes.values() if n.is_support_source]
    if support_sources:
        days_since_support_mention = min(
            (datetime.utcnow() - n.last_mentioned).days for n in support_sources
        )
        if days_since_support_mention > 45:
            return build_support_network_nudge(support_sources)

    return None  # nothing worth surfacing
```

**Gate 2 — Timing gate (is now the right moment?):**

```python
def gate_2_timing(
    opportunity: CoachingOpportunity,
    conversation_mode: str,
    primary_emotion: EmotionClassification,
    background_state: BackgroundEmotionalState,
    relationship_stage: str,
    circadian_band: str
) -> bool:
    """
    Returns True only if conditions are right to surface the observation.
    Is deliberately conservative — defaults to False in ambiguous cases.
    """
    # Hard blocks: never coach in these conditions
    if conversation_mode == "crisis":
        return False
    if primary_emotion.crisis_flag:
        return False
    if primary_emotion.valence < -0.65:
        return False   # user is too distressed; coaching is intrusive
    if circadian_band == "late_night" and opportunity.urgency != "high":
        return False   # late night is not the time for reflective observations
    if relationship_stage in ["new", "acquaintance"]:
        return False   # too early to offer social observations

    # Soft blocks: reduce willingness
    if background_state.bes_label in ["significant_negative_drift", "deteriorating"]:
        if opportunity.coaching_type not in [
            CoachingType.STRENGTH_ACKNOWLEDGMENT,
            CoachingType.SUPPORT_NETWORK_NUDGE
        ]:
            return False  # when user is struggling, only affirming coaching

    # Emotional state check: user should be in a receptive state
    if primary_emotion.primary_label not in [
        "neutral", "curiosity", "contentment", "frustration",
        "ambivalence", "relief"
    ]:
        if opportunity.delivery_mode == "inline":
            return False  # defer to question or future session

    # Conversation mode check: social coaching should be topic-adjacent
    if conversation_mode not in ["social_coaching", "casual", "life_review"]:
        if opportunity.coaching_type not in [
            CoachingType.GENTLE_REFRAME,
            CoachingType.BOUNDARY_SUPPORT
        ]:
            opportunity.delivery_mode = "deferred"
            return False  # off-topic for current conversation mode

    return True
```

**Gate 3 — Recency gate (has this been said too recently?):**

```python
def gate_3_recency(
    opportunity: CoachingOpportunity,
    pattern: Optional[SocialPattern]
) -> bool:
    """
    Prevents repetitive surfacing of the same observation.
    """
    if pattern is None:
        return True

    if pattern.has_been_surfaced:
        days_since_surfaced = (datetime.utcnow() - pattern.last_observed).days
        if days_since_surfaced < 14:
            return False   # too recent; don't repeat
        if pattern.surface_count >= 3 and not pattern.user_acknowledged:
            return False   # surfaced 3 times without acknowledgment; stop pushing

    return True
```

### 6.5 Observation Text Generation

When all three gates pass, the observation text is generated. This is the only point in SC-4 that may invoke an LLM — and only for `PATTERN_REFLECTION` and `CONFLICT_NAVIGATION` types. All other types use templates:

```python
OBSERVATION_TEMPLATES = {
    CoachingType.RELATIONSHIP_CHECK_IN: [
        "You haven't mentioned {name} in a while — how are things there?",
        "I realized I haven't heard about {name} lately. Is everything okay between you two?",
    ],
    CoachingType.SUPPORT_NETWORK_NUDGE: [
        "I've noticed you've been carrying a lot lately — have you been able to lean on anyone?",
        "Is there someone in your life you've been able to talk to about all of this?",
    ],
    CoachingType.STRENGTH_ACKNOWLEDGMENT: [
        "I want to name something — the way you handled that showed real maturity.",
        "That boundary you set with {name} — that took courage. Seriously.",
    ],
    CoachingType.BOUNDARY_SUPPORT: [
        "Setting that limit with {name} sounds like exactly the right call. It's okay that it's uncomfortable.",
        "The fact that it feels hard to hold that boundary doesn't mean you're wrong to have it.",
    ],
}
```

For `PATTERN_REFLECTION` and `CONFLICT_NAVIGATION`, a small LLM call generates the observation using the pattern's `coaching_hook` and `plain_language_description`:

```
SYSTEM:
Generate a 1–2 sentence observation that gently reflects a social pattern back to the user.
Be warm, non-judgmental, and non-prescriptive. Do not diagnose. Do not tell them what to do.
Frame as something you've noticed, not something you're certain about.

Pattern: {pattern.plain_language_description}
Coaching hook: {pattern.coaching_hook}
Person involved: {person.display_name} ({person.relationship_type})
User's current emotional state: {primary_emotion_label}
Relationship stage: {relationship_stage}

Generate observation (1–2 sentences maximum):
```

---

## 7. Sub-Component 5 — Social Coaching Response Modifier

### 7.1 Purpose

The Social Coaching Response Modifier takes the `CoachingOpportunity` from SC-4 and the `FinalResponsePacket` from Layer 4, and produces a modified response that integrates the coaching observation naturally. It does not replace the Layer 4 response — it augments it.

The word *naturally* is critical. A coaching observation bolted awkwardly onto the end of a response breaks flow and feels intrusive. The modifier's job is to find the right structural position, the right transition, and the right phrasing weight so that the observation reads as part of a coherent, human-like response.

### 7.2 Injection Modes

The observation can be injected in three positions, determined by `delivery_mode`:

**Mode 1 — Inline injection (at end of response body):**
Used when the observation is short, directly relevant to the current topic, and emotionally non-intrusive. The observation is appended with a soft transition:

```
[Layer 4 response body]

[soft transition phrase] + [observation_text]
```

Soft transition phrases (selected based on relationship stage and observation type):
- "I've also been thinking —" (established/close stage)
- "Can I add something I've noticed?" (developing stage)
- "One thing that's been on my mind —" (established/close stage)
- "Unrelated but —" (casual, low-stakes observation)

**Mode 2 — As question (at very end, as final element):**
Used when the observation is better framed as a question that opens a conversation rather than a statement:

```
[Layer 4 response body]

[question framed from observation_text]
```

**Mode 3 — Deferred (no injection this turn; flag for Layer 6):**
When timing gate fails but the observation is valid, it is passed to Layer 6 (Proactivity) as a pending coaching observation for a future session. The current response passes through unchanged.

### 7.3 Injection Decision Logic

```python
def inject_observation(
    final_response: FinalResponsePacket,
    opportunity: CoachingOpportunity,
    voice_parameters: VoiceParameters
) -> FinalResponsePacket:

    if opportunity.delivery_mode == "deferred":
        # Do not modify response; log for Layer 6
        return final_response

    if opportunity.delivery_mode == "proactive_future":
        # Do not modify response; log for Layer 6 proactive queue
        return final_response

    # Check response length headroom
    current_length = len(final_response.final_text)
    headroom = voice_parameters.max_response_length_chars - current_length

    if headroom < opportunity.max_length_chars:
        # Not enough space; defer
        opportunity.delivery_mode = "deferred"
        return final_response

    # Select transition phrase based on relationship stage and mode
    if opportunity.delivery_mode == "as_question":
        modified_text = final_response.final_text.rstrip() + "

" + opportunity.observation_text
    else:
        transition = select_transition(voice_parameters, opportunity.coaching_type)
        modified_text = (
            final_response.final_text.rstrip() +
            "

" + transition + " " + opportunity.observation_text
        )

    return FinalResponsePacket(
        **final_response.dict(),
        final_text=modified_text,
        social_coaching_injected=True,
        coaching_type_injected=opportunity.coaching_type,
        coaching_person_id=opportunity.triggering_person
    )
```

### 7.4 Consent Gate for Pattern Reflection

For `PATTERN_REFLECTION` coaching specifically — the type where Nova explicitly names a recurring dynamic — the system applies an **explicit framing rule**: Nova must frame the observation as something it has noticed, not as a conclusion it has reached. This is a hard prompt constraint:

✅ **Allowed:** "I've noticed a pattern that I wanted to mention — you've described similar tension with Riya around shared space a few times now. Does that feel accurate to you?"

❌ **Not allowed:** "You have a recurring conflict pattern with Riya about shared space."

❌ **Not allowed:** "It seems like your relationship with Riya is fundamentally about control."

The distinction: the first invites the user to confirm or reject. The second and third make authoritative statements about third parties the system cannot actually know. Pattern observations must always be presented as provisional and open to the user's correction.

---

## 8. The SocialIntelligencePacket — Layer 5 Output

```python
class SocialIntelligencePacket:

    # Updated social graph
    social_graph_updated: bool
    social_graph_version: int               # incremented if graph changed this turn

    # Events detected this session
    events_detected: list[SocialEvent]      # events found in current message
    events_pending_confirmation: list[SocialEvent]  # tentative matches awaiting confirmation

    # Active patterns
    active_patterns: list[SocialPattern]    # all currently active patterns

    # Coaching outcome
    coaching_opportunity_detected: bool
    coaching_opportunity: Optional[CoachingOpportunity]
    coaching_injected: bool                 # True = modified Layer 4 response
    coaching_deferred: bool                 # True = queued for Layer 6

    # Modified response (if coaching was injected)
    modified_response: Optional[FinalResponsePacket]
    # If None: Layer 4 FinalResponsePacket passes through unchanged

    # Layer 6 handoff
    proactive_coaching_queue: list[CoachingOpportunity]  # for future sessions

    # Social context summary (for Layer 4 future sessions via Layer 2)
    social_context_update: Optional[SocialContextUpdate]  # what to write to UWM

    # Audit
    sc1_updated: bool
    sc2_events_found: int
    sc3_patterns_evaluated: int
    sc3_patterns_active: int
    processing_latency_ms: int
```

---

## 9. Layer 5 and the User World Model

Layer 5 is the primary writer to the **Social Context** section of the User World Model (Layer 2). After each session, the following fields in the UWM are updated:

```python
class SocialContextUpdate:
    # Relationship graph changes
    nodes_added: list[str]              # new person_ids added
    nodes_updated: list[str]            # person_ids with updated valence/status
    nodes_gone_stale: list[str]         # person_ids not mentioned in 90+ days

    # Active social situations
    active_conflicts: list[dict]        # {person_id, conflict_summary, intensity}
    recent_positive_events: list[dict]  # {person_id, event_summary}

    # Pattern updates
    patterns_newly_detected: list[str]  # pattern_ids
    patterns_resolved: list[str]        # pattern_ids that are no longer active

    # Support network health
    support_network_size: int           # number of active support sources
    support_network_health: Literal[
        "robust",           # 3+ consistent support sources
        "adequate",         # 1–2 support sources
        "thin",             # 1 support source only
        "isolated"          # no consistent support sources
    ]

    # Social engagement trend (30-day rolling)
    social_engagement_trend: Literal["increasing", "stable", "decreasing", "insufficient_data"]
```

This social context is what Layer 2 makes available at the start of each session via the UWM context snapshot, so that Layer 4's Semantic Planner has current knowledge of the user's social world when constructing responses even in sessions where social topics are not discussed.

---

## 10. Coaching Ethics and Hard Constraints

Layer 5 operates on information about third parties — people who have not consented to being discussed with an AI system. This creates ethical obligations that are implemented as hard architectural constraints, not soft guidelines.

### Constraint 1 — Never advise against a person
Nova does not tell the user to cut off, avoid, or diminish any relationship. Observations about patterns are framed as invitations to reflect, not directives to act.

Implementation: The Observation Text Generator is explicitly prompted: "Do not suggest the user should end, distance from, or substantially change their relationship with this person."

### Constraint 2 — Never build a case against a third party
Nova does not accumulate evidence to build a prosecutorial case against a person in the user's life. Even if a person has been described negatively 10 times, Nova's observations frame this as what the user has experienced, not as facts about the person.

Implementation: All observation text uses "you've described" / "from what you've shared" framing, never "they are" / "they always" framing.

### Constraint 3 — Third-party data is held in minimum necessary form
Social Graph nodes contain summaries, not raw text. The event store contains extracted descriptions, not verbatim quotes. This minimizes the sensitivity of the stored data.

Implementation: Event extraction always produces `summary` and `user_perspective` fields — compressed, neutral descriptions — never the raw conversation text.

### Constraint 4 — User can delete any social node
The user can at any time instruct Nova to forget a person entirely. This triggers immediate deletion of the SocialNode, all associated SocialEvents, and all SocialPatterns that involved only that person. Patterns involving multiple people are retained with that person_id anonymized.

Implementation: A `DELETE_SOCIAL_NODE` command in the user management interface triggers a cascade delete in the social graph and event store.

### Constraint 5 — Coaching is always the user's choice to engage with
When Nova surfaces a pattern observation, it explicitly frames it as optional for the user to engage with. If the user says "not now" or ignores it, that is treated as an explicit signal: `user_acknowledged = False` for this pattern, and the next surfacing attempt is deferred by at least 30 days.

---

## 11. Error Handling and Fallback Behavior

| Failure Case | Fallback Behavior |
|---|---|
| Entity resolution fails (all confidence < 0.65) | Create tentative node; require 2 more mentions before committing |
| Event extraction LLM call fails | Mark session as `events_pending_extraction`; retry in background |
| Social Graph unavailable (read error) | SC-2 through SC-5 skip; FinalResponsePacket passes through unchanged; log error |
| Pattern detection runs but finds no patterns | Normal; SocialIntelligencePacket reflects empty pattern list |
| SC-4 gates all fail | No coaching injected; FinalResponsePacket unchanged |
| SC-5 injection overflows response length | Defer observation to Layer 6 queue; pass through original response |
| UWM write fails after session | Buffer update; retry on next session start |

**Hard rule:** Layer 5 never blocks the delivery of the Layer 4 response. If Layer 5 processing fails for any reason, the FinalResponsePacket passes through unchanged and the error is logged for background repair.

---

## 12. Performance Targets

| Operation | Target Latency | Notes |
|---|---|---|
| SC-1 Social Graph read | < 5ms | Cached in session |
| SC-2 Rule-based event detection | < 5ms | Regex matching |
| SC-4 Gates 1–3 | < 10ms | Deterministic lookups |
| SC-5 Template injection | < 5ms | No LLM call |
| SC-5 Pattern reflection LLM call | < 200ms | Small model; short prompt |
| SC-3 Pattern detection (batch) | < 2,000ms | Background; every 5 sessions |
| SC-2 LLM event extraction (batch) | < 1,000ms | Background; post-session |
| **Total on live response path (no coaching)** | **< 20ms** | Background processing only |
| **Total on live response path (with coaching)** | **< 220ms** | +SC-5 LLM call if pattern reflection |

---

## 13. Design Principles Summary

1. **Social context is longitudinal, not per-message.** SC-1 through SC-3 operate over sessions, not turns. This is what distinguishes social intelligence from conversational context. A single message rarely reveals a social pattern; 20 sessions might.

2. **The Social Graph is what the user said, not what Nova inferred.** Every node and edge in the graph is grounded in explicit user statements. Nova does not speculate about relationships not mentioned. Data source is always `"user_stated"`.

3. **Third parties are not in the room.** Nova has access to one side of every relationship: the user's account. Observations must always be framed as accounts, not facts. Observations about people must always leave room for the other side.

4. **Coaching is offered, not imposed.** The three-gate model exists to be conservative. If there is any doubt about timing, emotional readiness, or relational appropriateness, the observation is deferred. The default is silence, not intervention.

5. **Social intelligence serves the user's growth, not Nova's engagement metrics.** Layer 5 is not designed to keep the user talking. Surfacing pattern observations that the user doesn't want creates friction and damages trust. The recency gate and acknowledgment tracking exist specifically to prevent over-surfacing.

6. **Pattern reflection is provisional, always.** Nova presents patterns as things it has noticed, not conclusions it has reached. The user is the authority on their own relationships. Nova's observations are data points in the user's reflection process — not diagnostic outputs.

---

## 14. Implementation Notes (as-built)

This section records how the specification above is realized in `backend/layer5_relationship/`. The code is the single source of truth; §1–13 are the design intent.

### 14.1 Module map

| Spec sub-component | Module | Key entry point |
|---|---|---|
| SC-1 Social Graph Manager | `social_graph.py` | `resolve_entity`, `infer_relationship_from_context`, `create_node`, `update_node_valence`, `decay_confidence`, `is_tentative_match` |
| SC-2 Interpersonal Event Tracker | `event_tracker.py` | `detect_events_rule_based`, `extract_events`, `EVENT_DETECTION_RULES` |
| SC-3 Social Pattern Recognizer | `pattern_recognizer.py` | `detect_patterns`, `cluster_by_semantic_similarity`, `compute_mention_counts_by_window`, `is_declining_trend` |
| SC-4 Coaching Opportunity Detector | `coaching_detector.py` | `detect_coaching_opportunity`, `gate_1_availability`, `gate_2_timing`, `gate_3_recency` |
| SC-5 Social Coaching Response Modifier | `coaching_modifier.py` | `inject_observation`, `select_transition` |
| SocialIntelligencePacket orchestration | `packet_builder.py` | `build_social_intelligence_packet`, `build_social_context_update` |
| All dataclasses / enums | `schemas.py` | — |

### 14.2 Type reuse and dependency direction

The pipeline runs L1→L2→L3→L4→L5, so Layer 5 imports rather than redefines upstream types: `FinalResponsePacket` and `VoiceParameters` from Layer 4; `EmotionClassification`, `BackgroundEmotionalState`, `EmotionIntentPacket` from Layer 3; `ConversationMode` (via Layer 4) from Layer 2. Layer 5 owns the richer `SocialGraph` / `SocialNode` / `SocialEdge` / `SocialEvent` / `SocialPattern` model — distinct from Layer 2's lighter UWM `RelationshipGraph` / `PersonNode` snapshot, which Layer 5 *writes to* via `SocialContextUpdate` (§9).

A new field group was added to Layer 4's `FinalResponsePacket` so SC-5 can mark injection (per §7.3): `social_coaching_injected`, `coaching_type_injected`, `coaching_person_id` (all default to no-injection).

### 14.3 Dependency injection for offline testability

The two LLM uses are injected as plain callables: SC-2 event extraction (`llm_fn`, the post-session Pass 2) and the SC-4/orchestrator pattern-reflection / conflict-navigation text (`observation_llm_fn`). The embedding-dependent steps — entity resolution (SC-1) and conflict-topic clustering (SC-3) — accept an injected `similarity_fn` with token-overlap defaults (overlap coefficient for clustering, used because short topic phrases share few tokens). With nothing injected the layer degrades exactly as §11 prescribes and the rule-based paths run fully offline, which is what the unit suite exercises.

### 14.4 Behavioral deviations from the design text

- **Entity-resolution embeddings.** §3.4 computes `embed()` cosine inline; the implementation makes the semantic comparison an injected `similarity_fn` (skipped when absent), so alias and relationship-type matching still work with zero ML dependencies.
- **Clustering similarity.** §5.4 references a generic semantic-similarity cluster; the offline default is the **overlap coefficient** (`|A∩B|/min(|A|,|B|)`), not Jaccard — short conflict-topic summaries share too few tokens for Jaccard to group reliably. An embedding `similarity_fn` can be injected to match production.
- **Regex typos.** The §4.4 `EVENT_DETECTION_RULES` contain duplicated alternations (`argument|argument`, `didn't|didn't`); these are deduped in code. Two high-value rules absent from the doc's five examples (`support_received`, `conflict_resolution`) were added so SC-3 can recognize positive and resolution dynamics.
- **Deferred vs. absent opportunity.** `detect_coaching_opportunity` returns a populated opportunity with `opportunity_detected=False` and `delivery_mode="deferred"` when availability passes but timing/recency fails — the orchestrator queues these for Layer 6. An empty opportunity (no `coaching_type`) means nothing was available.
- **Pattern batch cadence.** §5.4 runs SC-3 every 5 sessions as a background job; `detect_patterns` is a pure function over the full event history, so the cadence is the scheduler's concern. The orchestrator consumes already-computed `active_patterns`.

### 14.5 Ethics constraints (§10) as implemented

- Pattern-reflection observations are framed provisionally — "I've noticed … Does that feel accurate to you?" — never as verdicts (Constraint 2; §7.4). The orchestrator's LLM prompt repeats the non-prescriptive, non-diagnostic framing.
- Events store only a neutral `summary` + `user_perspective`, never raw text (Constraint 3).
- The three-gate model defaults to silence; the recency gate stops surfacing after 3 unacknowledged attempts (Constraint 5).

### 14.6 Test coverage

63 unit tests across six files exercise every sub-component and the orchestrator:
`test_social_graph.py` (12), `test_event_tracker.py` (12), `test_pattern_recognizer.py` (9), `test_coaching_detector.py` (16), `test_coaching_modifier.py` (7), `test_layer5_packet_builder.py` (7). Coverage includes entity resolution across all match kinds + confidence decay; rule-based and LLM-fallback event extraction; intra/cross/temporal pattern detection with longitudinal spans; all three coaching gates (incl. crisis/distress/stage hard blocks and the negative-drift soft block); inline vs as-question injection with the headroom guard; provisional pattern framing; and the §11 hard rule (any internal failure passes the Layer 4 response through unchanged).

---

*This document specifies Layer 5 completely. All five sub-components have full schemas, all algorithms are specified with exact logic, and all gaps in the original design — the Social Graph Manager schema, entity resolution mechanism, event taxonomy and detection, pattern recognition algorithm, coaching opportunity gating, response injection mechanics, UWM social context update contract, and ethical constraints for third-party data — are fully resolved. Section 14 records the as-built implementation. No behavior of Layer 5 requires assumptions or inferences from other documents.*
