# Layer 7 — Goals & Accountability Engine
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

Layer 7 is the **goals and accountability layer** — the part of NovaAI that tracks what the user wants to achieve, monitors their progress over time, and holds the thread of those intentions across sessions, weeks, and months without the user having to constantly re-state them.

The distinction between Layer 7 and every other part of the system is orientation in time. Every other layer is anchored in the present or recent past — what the user said, how they're feeling, what happened last week. Layer 7 is anchored in the **future the user has described wanting**. It is the engine that makes Nova not just empathetic about where a person *is*, but genuinely invested in where they're *going*.

This is not a task manager. Layer 7 does not create to-do lists or send reminders to drink water. It tracks **meaningful, self-directed intentions** — the goals that people mention in conversation because they matter to them, not because they were entered into a formal system. A user who says "I really want to get fit before summer" has just created a Layer 7 goal. A user who says "I've been trying to cut back on drinking and it's hard" has just created a Layer 7 goal. Neither statement was addressed to a goal system. Both statements contain an intention, a direction, and an implied desire to be held to account for it.

Layer 7 contains **five sub-components**:

- **SC-1: Goal Extractor** — detects, extracts, and formalizes goals from unstructured conversation
- **SC-2: Goal Store** — persistent, structured store of all user goals with full lifecycle management
- **SC-3: Progress Monitor** — continuously infers progress from conversational signals and updates goal state
- **SC-4: Accountability Response Modifier** — injects goal awareness into active conversations when appropriate
- **SC-5: Goal Decomposer** — breaks large goals into milestones and habits; interfaces with Layer 6

---

## 2. Architecture Overview

```
Inputs to Layer 7:

Per-message (from Layer 1 + Layer 2 output):
 ├── user_message_text
 ├── classified_intent (from Layer 1)
 ├── emotional_state (from Layer 1)
 ├── retrieved_memories (from Layer 2)
 └── session_context

Post-session (background, from Layer 2 State Updater):
 └── session_summary (after session ends)

Background poll (every 24h):
 └── goal_store scan for due milestones and stale goals

                    │
                    ▼
     ┌──────────────────────────────────────┐
     │  SC-1: Goal Extractor                │  Per-message, background
     │  (detect + formalize new goals)      │  LLM call; runs async
     └──────────────────────────────────────┘
                    │ GoalExtractionResult
                    ▼
     ┌──────────────────────────────────────┐
     │  SC-2: Goal Store                    │  Always running; persistent
     │  (lifecycle management + retrieval)  │  Read on every message
     └──────────────────────────────────────┘
                    │
         ┌──────────┴──────────────────────┐
         │                                 │
         ▼                                 ▼
┌────────────────────┐         ┌────────────────────────┐
│  SC-3: Progress    │         │  SC-5: Goal Decomposer │
│  Monitor           │         │  (milestones + habits  │
│  (inference +      │         │   + Layer 6 handoff)   │
│   state update)    │         └────────────────────────┘
└────────────────────┘                    │
         │                                │ ProactiveItem
         │ GoalContextPacket              ▼
         ▼                      Layer 6 Proactive Queue
┌────────────────────┐
│  SC-4: Accountabil-│
│  ity Response      │  Per-message; conditional
│  Modifier          │
└────────────────────┘
         │
         ▼
  Layer 4 Response Generator
  (GoalContextPacket injected into prompt)

Outputs from Layer 7:
 ├── GoalContextPacket → Layer 4 (per message, if goals are relevant)
 ├── ProactiveItems → Layer 6 (milestone approaching; stale goal; celebration)
 ├── GoalStateUpdate → Layer 2 UWM (goal status changes; new goals; completions)
 └── Layer7Output → Layer 12 Audit Log
```

**Execution model:**
- SC-1 runs **asynchronously** after each message — it does not block response generation
- SC-2 is read synchronously on every message to check for relevant active goals
- SC-3 runs synchronously in the message pipeline (deterministic inference) + asynchronously for complex progress updates
- SC-4 runs synchronously in the pipeline when SC-2 returns relevant goals
- SC-5 runs asynchronously after goal creation or milestone events; writes to Layer 6

---

## 3. Sub-Component 1 — Goal Extractor

### 3.1 Purpose

The Goal Extractor is the detection and formalization engine. Its job is to identify when the user has expressed a meaningful intention — explicit or implicit — and convert that natural language statement into a structured `Goal` object that the system can track.

This is the hardest sub-component to get right because goals are almost never expressed in structured language. People do not say "I would like to set a goal: fitness, target: lose 5kg, deadline: August." They say "I really need to get my act together with exercise" or "I told myself this year would be different" or "I've been wanting to learn guitar for like two years but never actually start." All three are goals. None of them look like goals to a rule-based system.

### 3.2 Goal Signal Types

Before extraction, Goal Extractor classifies the user's statement into one of four signal strengths:

```python
class GoalSignalStrength(str, Enum):
    EXPLICIT_STATED   = "explicit_stated"    # "I want to / I'm trying to / my goal is to"
    IMPLICIT_ASPIRED  = "implicit_aspired"   # "I wish I could / I've been meaning to"
    REPEATED_THEME    = "repeated_theme"     # same aspiration mentioned in 2+ sessions
    ABANDONED_REVISIT = "abandoned_revisit"  # something user tried before and is trying again
```

Only `EXPLICIT_STATED` and `IMPLICIT_ASPIRED` create new goals immediately.
`REPEATED_THEME` upgrades an existing `tentative` goal to `active`.
`ABANDONED_REVISIT` reactivates an `abandoned` or `completed` goal from the store.

### 3.3 Extraction Trigger Logic

Goal Extractor runs on every message but uses a **fast pre-filter** before invoking the LLM:

```python
GOAL_SIGNAL_KEYWORDS = [
    # Explicit
    "want to", "trying to", "working on", "my goal", "i plan to",
    "i'm going to", "decided to", "i need to", "committed to",
    # Implicit
    "wish i could", "been meaning to", "always wanted", "someday",
    "keep putting off", "never get around to", "i should",
    # Progress updates (may update existing goals)
    "got further", "slipped up", "back on track", "gave up on",
    "finished", "completed", "hit my", "made progress",
]

def should_run_extractor(message: str) -> bool:
    message_lower = message.lower()
    return any(kw in message_lower for kw in GOAL_SIGNAL_KEYWORDS)
```

If the pre-filter passes, the LLM extraction call runs asynchronously (does not block response).

### 3.4 Extraction Prompt

```
SYSTEM:
You are a goal extraction specialist. Your task is to identify whether the user
has expressed a meaningful personal intention, aspiration, or goal in their message.

A goal is: a stated desire to achieve something, change a behavior, or reach a state
that requires sustained effort over time. Single-use tasks ("buy milk") are NOT goals.
Emotional venting without direction ("I hate my job") is NOT a goal unless paired
with an intent to change.

User message: {user_message}

Prior context (last 3 turns): {prior_context}

User's existing active goals (for deduplication): {active_goal_summaries}

Instructions:
1. Identify whether a new goal is expressed, or an existing goal is being updated.
2. If a new goal: extract the goal in structured form (see schema below).
3. If an update to an existing goal: return the goal_id and the update type.
4. If no goal is present: return null.
5. Do NOT infer goals that are not present. If uncertain, set confidence < 0.6.

Return JSON:
{
  "goal_detected": true/false,
  "is_update": true/false,
  "goal_id_if_update": null or "string",
  "update_type": null or "progress_positive" | "progress_negative" | "abandoned" | "completed",
  "update_description": null or "string",
  "new_goal": null or {
    "raw_statement": "exact quote from user message",
    "inferred_title": "concise 3-7 word title",
    "inferred_domain": "health | career | relationships | learning | finance | creativity | personal_growth | other",
    "inferred_direction": "achieve_outcome | build_habit | stop_behavior | maintain_state | develop_skill",
    "has_explicit_deadline": true/false,
    "deadline_description": null or "string as stated",
    "has_explicit_metric": true/false,
    "metric_description": null or "string as stated",
    "emotional_weight": 0.0-1.0,
    "confidence": 0.0-1.0,
    "signal_strength": "explicit_stated | implicit_aspired"
  }
}
```

### 3.5 Deduplication Logic

Before creating a new goal, the extractor checks semantic similarity against existing active goals:

```python
def is_duplicate_goal(
    new_goal_embedding: list[float],
    active_goals: list[Goal]
) -> tuple[bool, Optional[str]]:
    for goal in active_goals:
        similarity = cosine_similarity(new_goal_embedding, goal.title_embedding)
        if similarity > 0.82:
            return True, goal.goal_id   # duplicate; return existing goal ID
    return False, None
```

If a duplicate is detected, the new statement is logged as a `reaffirmation_event` on the existing goal — which reinforces it and updates `last_mentioned_at` — rather than creating a redundant goal.

### 3.6 GoalExtractionResult Schema

```python
class GoalExtractionResult:
    extraction_timestamp: datetime
    message_id: str
    goal_detected: bool
    is_update: bool
    goal_id_if_update: Optional[str]
    update_type: Optional[str]
    update_description: Optional[str]
    new_goal_data: Optional[dict]       # raw JSON from LLM
    confidence: float
    was_duplicate: bool
    matched_goal_id: Optional[str]      # if duplicate
    processing_time_ms: int
```

---

## 4. Sub-Component 2 — Goal Store

### 4.1 Purpose

The Goal Store is the persistent, structured repository for all user goals, their full history, their current state, and all events that have occurred against them. It is the source of truth for everything Layer 7 knows about the user's intentions.

### 4.2 Goal Schema — Core

```python
class GoalDomain(str, Enum):
    HEALTH          = "health"
    CAREER          = "career"
    RELATIONSHIPS   = "relationships"
    LEARNING        = "learning"
    FINANCE         = "finance"
    CREATIVITY      = "creativity"
    PERSONAL_GROWTH = "personal_growth"
    OTHER           = "other"

class GoalDirection(str, Enum):
    ACHIEVE_OUTCOME  = "achieve_outcome"   # reach a specific end state
    BUILD_HABIT      = "build_habit"       # establish a recurring behavior
    STOP_BEHAVIOR    = "stop_behavior"     # eliminate a behavior
    MAINTAIN_STATE   = "maintain_state"    # preserve something already achieved
    DEVELOP_SKILL    = "develop_skill"     # improve at something over time

class GoalStatus(str, Enum):
    TENTATIVE        = "tentative"         # mentioned once; not yet confirmed important
    ACTIVE           = "active"            # confirmed goal; actively tracking
    ON_TRACK         = "on_track"          # recent positive progress signals
    AT_RISK          = "at_risk"           # stale or negative signals; needs attention
    PAUSED           = "paused"            # user explicitly paused; not abandoned
    ABANDONED        = "abandoned"         # user explicitly gave up or stopped mentioning
    COMPLETED        = "completed"         # user has indicated achievement
    ARCHIVED         = "archived"          # too old + no signals; removed from active view

class Goal:
    # Identity
    goal_id: str                            # stable UUID
    user_id: str
    title: str                              # concise 3-7 word title
    title_embedding: list[float]            # for deduplication + retrieval
    raw_statement: str                      # original user quote at creation
    domain: GoalDomain
    direction: GoalDirection

    # Content
    description: str                        # fuller description (may be elaborated over time)
    outcome_definition: Optional[str]       # what does "done" look like? may be user-stated or inferred
    motivation_notes: Optional[str]         # why this matters to the user (from conversation)
    obstacles_noted: list[str]              # obstacles the user has mentioned
    strategies_noted: list[str]             # approaches the user has mentioned trying
    prior_attempts: int                     # how many times user has tried this before (from conversation)

    # Timing
    created_at: datetime
    deadline: Optional[datetime]            # explicit if stated; None if open-ended
    deadline_description: Optional[str]     # "before summer", "by my birthday" etc.
    deadline_is_inferred: bool              # True if inferred from context, not stated
    last_mentioned_at: datetime             # most recent session where goal was mentioned
    last_progress_at: Optional[datetime]    # most recent positive progress signal
    last_setback_at: Optional[datetime]     # most recent negative progress signal
    first_active_at: Optional[datetime]     # when status changed from tentative to active

    # Status and progress
    status: GoalStatus
    progress_score: float                   # 0.0-1.0; continuously updated
    progress_trend: Literal[
        "improving", "stable", "declining", "unknown"
    ]
    momentum_score: float                   # 0.0-1.0; based on recency and frequency of progress signals
    confidence_at_creation: float           # extractor confidence when goal was first created

    # Metric and measurement
    has_metric: bool
    metric_description: Optional[str]       # user-stated metric ("lose 5kg", "save 10k")
    metric_unit: Optional[str]
    metric_target: Optional[float]
    metric_current: Optional[float]         # if user has stated a current value
    metric_at_creation: Optional[float]

    # Emotional weight
    emotional_weight: float                 # 0.0-1.0; how much this matters to the user
    emotional_weight_updated_at: datetime

    # Milestones (from SC-5)
    milestones: list[Milestone]
    habits: list[Habit]

    # Signals log
    signal_events: list[GoalSignalEvent]    # full history of all mentions and updates

    # Layer 6 handoff state
    proactive_items_created: list[str]      # item IDs created in Layer 6 for this goal
    last_proactive_sent_at: Optional[datetime]
```

### 4.3 GoalSignalEvent Schema

Every mention, update, or inference about a goal is logged as a `GoalSignalEvent`:

```python
class GoalSignalEventType(str, Enum):
    CREATED              = "created"
    REAFFIRMED           = "reaffirmed"       # user mentioned goal again without update
    PROGRESS_POSITIVE    = "progress_positive" # "I went to the gym 3x this week"
    PROGRESS_NEGATIVE    = "progress_negative" # "I slipped up", "haven't done it in a while"
    OBSTACLE_MENTIONED   = "obstacle_mentioned"
    STRATEGY_MENTIONED   = "strategy_mentioned"
    MOTIVATION_EXPRESSED = "motivation_expressed"
    DEADLINE_UPDATED     = "deadline_updated"
    METRIC_UPDATED       = "metric_updated"
    STATUS_CHANGED       = "status_changed"
    MILESTONE_REACHED    = "milestone_reached"
    MILESTONE_MISSED     = "milestone_missed"
    HABIT_CHECKED        = "habit_checked"
    ABANDONED            = "abandoned"
    COMPLETED            = "completed"
    PROACTIVE_SENT       = "proactive_sent"   # Layer 6 sent a check-in for this goal
    PROACTIVE_RESPONDED  = "proactive_responded"

class GoalSignalEvent:
    event_id: str
    goal_id: str
    event_type: GoalSignalEventType
    timestamp: datetime
    session_id: str
    evidence_text: str                  # the user's words that triggered this event
    inferred: bool                      # True if inferred; False if explicitly stated
    confidence: float
    progress_delta: Optional[float]     # +/- change in progress_score this event caused
    status_before: Optional[GoalStatus]
    status_after: Optional[GoalStatus]
    metadata: dict                      # event-type specific data
```

### 4.4 Milestone and Habit Schemas

```python
class MilestoneStatus(str, Enum):
    PENDING     = "pending"
    REACHED     = "reached"
    MISSED      = "missed"
    DEFERRED    = "deferred"

class Milestone:
    milestone_id: str
    goal_id: str
    title: str
    description: str
    target_date: Optional[datetime]
    status: MilestoneStatus
    created_at: datetime
    created_by: Literal["system", "user"]   # system = inferred by SC-5; user = user-stated
    reached_at: Optional[datetime]
    evidence: Optional[str]                 # user's words confirming milestone reached
    progress_weight: float                  # how much this milestone contributes to overall progress

class HabitFrequency(str, Enum):
    DAILY       = "daily"
    WEEKLY      = "weekly"
    WEEKDAYS    = "weekdays"
    CUSTOM      = "custom"

class Habit:
    habit_id: str
    goal_id: str
    title: str
    description: str
    frequency: HabitFrequency
    target_count_per_period: int            # e.g., 3x per week
    current_streak: int                     # consecutive periods met
    best_streak: int
    total_check_ins: int
    last_checked_in: Optional[datetime]
    status: Literal["active", "paused", "abandoned"]
    created_at: datetime
```

### 4.5 Goal Retrieval Interface

SC-2 is queried synchronously on every message to find goals relevant to the current conversation:

```python
def get_relevant_goals(
    user_id: str,
    message_text: str,
    message_embedding: list[float],
    emotional_state: EmotionalState,
    max_results: int = 3
) -> list[RelevantGoal]:
    """
    Returns up to max_results goals ranked by relevance to current message.
    """
    active_goals = load_goals_by_status(user_id, statuses=[
        GoalStatus.ACTIVE, GoalStatus.ON_TRACK, GoalStatus.AT_RISK
    ])

    scored = []
    for goal in active_goals:
        # Semantic similarity: message vs goal title embedding
        semantic_score = cosine_similarity(message_embedding, goal.title_embedding)

        # Recency: how recently was this goal mentioned?
        days_since_mention = (datetime.utcnow() - goal.last_mentioned_at).days
        recency_score = math.exp(-0.05 * days_since_mention)  # decays slowly

        # Momentum: how active is this goal?
        momentum_score = goal.momentum_score

        # Status urgency: at-risk goals score higher
        status_bonus = 0.2 if goal.status == GoalStatus.AT_RISK else 0.0

        combined_score = (
            0.50 * semantic_score +
            0.25 * recency_score +
            0.15 * momentum_score +
            0.10 * goal.emotional_weight +
            status_bonus
        )
        scored.append((goal, combined_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [
        RelevantGoal(goal=g, relevance_score=s)
        for g, s in scored[:max_results]
        if s > 0.25  # minimum relevance threshold
    ]
```

### 4.6 Goal Status Transition Rules

Status transitions are governed by explicit rules, not arbitrary LLM judgment:

```python
STATUS_TRANSITIONS = {
    # From TENTATIVE
    ("tentative", "reaffirmed"):            "active",          # mentioned again → confirm it
    ("tentative", "progress_positive"):     "active",          # made progress on it
    ("tentative", "abandoned"):             "abandoned",
    ("tentative", "stale_30_days"):         "archived",        # not mentioned in 30 days

    # From ACTIVE / ON_TRACK / AT_RISK
    ("active", "progress_positive"):        "on_track",
    ("active", "stale_21_days"):            "at_risk",
    ("on_track", "progress_positive"):      "on_track",        # stays on track
    ("on_track", "progress_negative"):      "active",          # step back, still active
    ("on_track", "stale_14_days"):          "at_risk",
    ("at_risk", "progress_positive"):       "active",          # recovering
    ("at_risk", "stale_30_days"):           "abandoned",       # too stale
    ("at_risk", "abandoned"):               "abandoned",

    # Terminal transitions
    ("*", "completed"):                     "completed",       # user says they did it
    ("*", "abandoned"):                     "abandoned",       # user explicitly gives up
    ("*", "paused"):                        "paused",          # user explicitly pauses
    ("paused", "reaffirmed"):               "active",          # user comes back to it
    ("paused", "stale_90_days"):            "archived",
}
```

The `stale_N_days` triggers are evaluated by the **24-hour background scan** in SC-3.

---

## 5. Sub-Component 3 — Progress Monitor

### 5.1 Purpose

The Progress Monitor is responsible for continuously inferring how a goal is progressing from the user's natural language — without requiring structured updates. The user never has to say "goal ID 7, progress: 60%." They just say "I went for a run three days in a row this week" and the Progress Monitor handles the rest.

Progress inference has two modes: **synchronous inline inference** (fast, rule-based, runs per message) and **asynchronous deep inference** (LLM-assisted, runs post-session).

### 5.2 Synchronous Inline Progress Inference

Runs every message when SC-2 returns at least one relevant goal. Uses keyword classification to detect signal polarity:

```python
POSITIVE_PROGRESS_SIGNALS = [
    "did it", "completed", "finished", "made it", "went ahead", "actually did",
    "kept at it", "stuck to it", "back on track", "good week", "progress",
    "getting better", "improving", "feels easier", "didn't skip", "hit my",
    "hit a milestone", "streak", "consecutive", "getting closer",
]

NEGATIVE_PROGRESS_SIGNALS = [
    "slipped up", "messed up", "haven't", "failed to", "gave up on",
    "not doing it", "stopped", "quit", "too hard", "can't keep up",
    "fell off", "derailed", "skipped", "missed", "behind on",
    "haven't touched it", "totally forgot", "been avoiding",
]

COMPLETION_SIGNALS = [
    "done", "finished", "completed it", "achieved", "got there", "hit my goal",
    "made it", "crossed the finish line", "officially", "finally did it",
]

ABANDONMENT_SIGNALS = [
    "giving up", "gave up", "dropping it", "not worth it", "forget it",
    "decided not to", "changed my mind about", "not doing that anymore",
    "not realistic", "not the right time",
]

def classify_progress_signal(
    message: str,
    relevant_goal: Goal
) -> Optional[ProgressSignalClassification]:
    message_lower = message.lower()

    # Check completion first (highest confidence action)
    for sig in COMPLETION_SIGNALS:
        if sig in message_lower:
            return ProgressSignalClassification(
                signal_type="completed",
                confidence=0.85,
                evidence=message
            )

    # Check abandonment
    for sig in ABANDONMENT_SIGNALS:
        if sig in message_lower:
            return ProgressSignalClassification(
                signal_type="abandoned",
                confidence=0.80,
                evidence=message
            )

    # Check positive/negative progress
    positive_hits = sum(1 for s in POSITIVE_PROGRESS_SIGNALS if s in message_lower)
    negative_hits = sum(1 for s in NEGATIVE_PROGRESS_SIGNALS if s in message_lower)

    if positive_hits > 0 and positive_hits > negative_hits:
        return ProgressSignalClassification(
            signal_type="progress_positive",
            confidence=min(0.5 + 0.1 * positive_hits, 0.90),
            evidence=message
        )
    elif negative_hits > 0 and negative_hits > positive_hits:
        return ProgressSignalClassification(
            signal_type="progress_negative",
            confidence=min(0.5 + 0.1 * negative_hits, 0.90),
            evidence=message
        )

    return None  # No progress signal detected
```

### 5.3 Progress Score Update Formula

When a progress signal is detected, `progress_score` updates as:

\[
P_{	ext{new}} = P_{	ext{old}} + \Delta P 	imes C_{	ext{confidence}}
\]

Where:

```python
PROGRESS_DELTAS = {
    "progress_positive":    +0.10,
    "progress_negative":    -0.08,
    "milestone_reached":    +0.20,   # milestone weight varies; default 0.20
    "milestone_missed":     -0.05,
    "habit_checked":        +0.03,
    "reaffirmed":           +0.01,   # just mentioning the goal without update
    "obstacle_mentioned":   -0.02,
    "abandoned":             None,   # sets progress_score to current value; status → abandoned
    "completed":             1.0,    # sets progress_score to 1.0
}
```

`progress_score` is clamped to [0.0, 1.0].

### 5.4 Momentum Score

Momentum is distinct from progress — it measures the **rate and recency of engagement** with a goal, not the absolute progress:

\[
M = rac{1}{N} \sum_{i=1}^{N} e^{-\lambda \cdot d_i} 	imes w_i
\]

Where \(d_i\) is the number of days since the \(i\)-th signal event, \(w_i\) is the signal weight (positive progress = 1.0, negative = 0.5, reaffirmation = 0.3), and \(\lambda = 0.1\) (decay rate). \(N\) is the count of signal events in the last 30 days (max 20 most recent).

Momentum ∈ [0.0, 1.0]. High momentum (> 0.6) = user is actively working on this goal. Low momentum (< 0.2) = goal is going stale.

### 5.5 Asynchronous Deep Inference (Post-Session)

After each session ends, a background LLM call re-reads the full session summary and re-evaluates all active goals for progress signals that the fast inline inference may have missed (due to indirect language, multi-turn context, or embedded references):

```python
POST_SESSION_INFERENCE_PROMPT = """
You are a goal progress analyst. A user has just completed a conversation session.
Review the session summary and identify any signals about the following active goals:

Active goals:
{active_goal_summaries}

Session summary:
{session_summary}

For each goal, identify if the session contained:
1. A progress signal (positive or negative)
2. A completion event
3. An abandonment signal
4. A new obstacle or strategy mentioned
5. A motivation statement (why the goal matters)

Return JSON array — one entry per goal that had any relevant signal.
If a goal had no relevant signal in this session, omit it.

Schema per entry:
{
  "goal_id": "string",
  "signal_type": "progress_positive | progress_negative | completed | abandoned | obstacle | strategy | motivation | reaffirmed",
  "evidence": "exact quote or paraphrase from session",
  "confidence": 0.0-1.0,
  "inferred": true/false
}
"""
```

### 5.6 Stale Goal Detection (24h Background Scan)

Every 24 hours, a background job scans all active goals and applies staleness rules:

```python
def run_staleness_scan(user_id: str) -> list[GoalStateChange]:
    changes = []
    active_goals = load_goals_by_status(user_id, [
        GoalStatus.ACTIVE, GoalStatus.ON_TRACK, GoalStatus.AT_RISK, GoalStatus.TENTATIVE
    ])

    for goal in active_goals:
        days_since = (datetime.utcnow() - goal.last_mentioned_at).days

        # Apply transition rules for stale triggers
        if goal.status == GoalStatus.TENTATIVE and days_since >= 30:
            changes.append(GoalStateChange(goal_id=goal.goal_id,
                new_status=GoalStatus.ARCHIVED, reason="stale_30_days"))

        elif goal.status in [GoalStatus.ACTIVE, GoalStatus.ON_TRACK] and days_since >= 14:
            changes.append(GoalStateChange(goal_id=goal.goal_id,
                new_status=GoalStatus.AT_RISK, reason="stale_14_days"))

        elif goal.status == GoalStatus.AT_RISK and days_since >= 30:
            changes.append(GoalStateChange(goal_id=goal.goal_id,
                new_status=GoalStatus.ABANDONED, reason="stale_30_days"))

        # Create Layer 6 proactive item for AT_RISK goals that haven't had a proactive sent
        if goal.status == GoalStatus.AT_RISK:
            hours_since_proactive = float("inf")
            if goal.last_proactive_sent_at:
                hours_since_proactive = (
                    datetime.utcnow() - goal.last_proactive_sent_at
                ).total_seconds() / 3600

            if hours_since_proactive > 72:   # at least 3 days since last proactive
                create_goal_proactive_item(goal, item_type="GOAL_ENCOURAGEMENT")

    return changes
```

---

## 6. Sub-Component 4 — Accountability Response Modifier

### 6.1 Purpose

The Accountability Response Modifier is the **in-conversation** arm of Layer 7. Its job is to inject goal awareness into Nova's active responses when doing so is genuinely useful — acknowledging progress, gently noting a setback, connecting the current conversation to a goal the user cares about — without being mechanical, preachy, or robotic.

This is the most behaviorally sensitive part of Layer 7. Done well, goal references feel like a thoughtful friend connecting the dots. Done poorly, they feel like a productivity app tracking your stats. The modifier must thread that needle.

### 6.2 GoalContextPacket — Output to Layer 4

```python
class GoalContextPacket:
    # Set by SC-3 before packet is built
    relevant_goals: list[RelevantGoal]      # from SC-2 retrieval

    # Injection directive
    should_reference_goal: bool             # main decision: reference a goal or not
    reference_type: Optional[Literal[
        "acknowledge_progress",             # user made progress; acknowledge it
        "acknowledge_setback",              # user had a setback; be supportive
        "celebrate_completion",             # user completed a goal; celebrate
        "connect_topic",                    # current topic is related to goal; note it
        "gentle_check",                     # goal is stale; light touch mention
        "none"
    ]]
    primary_goal: Optional[Goal]            # the goal to reference (if any)

    # Progress signal
    progress_signal_detected: bool
    progress_signal_type: Optional[str]
    progress_signal_evidence: Optional[str]

    # New goal to create (from SC-1)
    new_goal_pending: Optional[GoalExtractionResult]

    # Response instructions for Layer 4
    response_instruction: Optional[str]     # plain language instruction for the LLM
    tone_instruction: Optional[str]         # e.g., "celebratory", "supportive", "light"
    max_goal_reference_chars: int           # how long the goal reference may be
    goal_reference_position: Literal[
        "opening", "body", "closing", "none"
    ]
```

### 6.3 Decision Logic — When to Reference a Goal

```python
def decide_goal_reference(
    relevant_goals: list[RelevantGoal],
    progress_signal: Optional[ProgressSignalClassification],
    emotional_state: EmotionalState,
    conversation_mode: str,
    relationship_stage: str
) -> GoalContextPacket:

    # NEVER reference goals in these modes
    BLOCKED_MODES = ["crisis", "emotional_support", "casual"]
    # Uses Layer 3's ConversationMode taxonomy: "crisis" (safety gate), "emotional_support"
    # (user needs support not goal pressure), "casual" (not the right context for goal references)
    if conversation_mode in BLOCKED_MODES:
        return GoalContextPacket(should_reference_goal=False, reference_type="none")

    # NEVER reference goals if relationship is too early
    if relationship_stage in ["new"]:
        return GoalContextPacket(should_reference_goal=False, reference_type="none")

    # If no relevant goals, nothing to reference
    if not relevant_goals:
        return GoalContextPacket(should_reference_goal=False, reference_type="none")

    top_goal = relevant_goals[0].goal

    # --- CASE 1: Explicit completion signal --------------------------------
    if progress_signal and progress_signal.signal_type == "completed":
        return GoalContextPacket(
            should_reference_goal=True,
            reference_type="celebrate_completion",
            primary_goal=top_goal,
            response_instruction=(
                f"The user has just completed their goal: '{top_goal.title}'. "
                f"Celebrate this genuinely. Reference how long they've been working on it "
                f"if known ({(datetime.utcnow() - top_goal.created_at).days} days). "
                f"Do not immediately pivot to what's next — sit in the win."
            ),
            tone_instruction="celebratory_warm",
            max_goal_reference_chars=150,
            goal_reference_position="opening"
        )

    # --- CASE 2: Positive progress signal -----------------------------------
    if progress_signal and progress_signal.signal_type == "progress_positive":
        return GoalContextPacket(
            should_reference_goal=True,
            reference_type="acknowledge_progress",
            primary_goal=top_goal,
            response_instruction=(
                f"The user has made progress on: '{top_goal.title}'. "
                f"Acknowledge it briefly — warmly but not over-the-top. "
                f"Do not make it the whole response unless they're talking only about this."
            ),
            tone_instruction="warm_encouraging",
            max_goal_reference_chars=100,
            goal_reference_position="body"
        )

    # --- CASE 3: Negative progress / setback --------------------------------
    if progress_signal and progress_signal.signal_type == "progress_negative":
        if emotional_state.valence < -0.5:
            # User is already feeling bad — don't pile on
            return GoalContextPacket(
                should_reference_goal=True,
                reference_type="acknowledge_setback",
                primary_goal=top_goal,
                response_instruction=(
                    f"The user has had a setback on: '{top_goal.title}'. "
                    f"They're already feeling down. Be supportive only. "
                    f"Do NOT offer advice unless they ask. Do NOT say 'it's okay' repeatedly. "
                    f"Acknowledge the difficulty; do not minimize it."
                ),
                tone_instruction="gentle_supportive",
                max_goal_reference_chars=80,
                goal_reference_position="opening"
            )
        else:
            # User is more matter-of-fact about the setback
            return GoalContextPacket(
                should_reference_goal=True,
                reference_type="acknowledge_setback",
                primary_goal=top_goal,
                response_instruction=(
                    f"The user had a setback on: '{top_goal.title}'. "
                    f"Acknowledge it; be briefly supportive; offer to help think through it "
                    f"if appropriate. Keep it light — this is one setback, not a verdict."
                ),
                tone_instruction="supportive_practical",
                max_goal_reference_chars=120,
                goal_reference_position="body"
            )

    # --- CASE 4: Topic is related to goal but no explicit signal ---------------
    if (relevant_goals[0].relevance_score > 0.65
            and top_goal.status in [GoalStatus.ACTIVE, GoalStatus.ON_TRACK]
            and top_goal.momentum_score > 0.3):
        return GoalContextPacket(
            should_reference_goal=True,
            reference_type="connect_topic",
            primary_goal=top_goal,
            response_instruction=(
                f"The user's current topic relates to their goal: '{top_goal.title}'. "
                f"You may briefly connect them if it feels natural. This must be organic — "
                f"a one-sentence link, not a lecture. Only do this once per session."
            ),
            tone_instruction="natural_casual",
            max_goal_reference_chars=60,
            goal_reference_position="closing"
        )

    # Default: no reference
    return GoalContextPacket(should_reference_goal=False, reference_type="none")
```

### 6.4 Anti-Patterns the Modifier Must Never Do

These are hard exclusions enforced via instruction in the Layer 4 prompt:

1. **Never announce the goal system** — "I noticed in my goal tracker that..." is robotic. Goal references must feel like organic recall, not system notifications.
2. **Never reference progress scores numerically** — "You're at 60% on your fitness goal" is clinical and weird. Progress is described naturally: "you've been really consistent lately."
3. **Never reference more than one goal per response** — even if two goals are relevant, only the highest-relevance goal is referenced.
4. **Never reference a goal in crisis mode** — no matter how relevant. Human distress overrides everything.
5. **Never ask about a goal if the user is on a different topic entirely** — a goal mention must be organic, not a pivot.

---

## 7. Sub-Component 5 — Goal Decomposer

### 7.1 Purpose

The Goal Decomposer takes a newly created or recently re-activated `active` goal and breaks it down into **milestones** (discrete checkpoints toward the outcome) and **habits** (recurring behaviors that support the goal). It also creates `ProactiveItem` entries in Layer 6 for upcoming milestones.

This sub-component runs **asynchronously** — it does not run on the message path. It triggers when a goal transitions to `active` status.

### 7.2 Decomposition Trigger

```python
def on_goal_status_change(goal: Goal, new_status: GoalStatus) -> None:
    if new_status == GoalStatus.ACTIVE and len(goal.milestones) == 0:
        schedule_decomposition(goal.goal_id, delay_seconds=30)
        # Runs after a 30s delay to avoid blocking any active session
```

### 7.3 Decomposition Prompt

```
SYSTEM:
You are a goal planning specialist. Your task is to break down a user's personal
goal into concrete milestones and supporting habits.

Goal: {goal_title}
Description: {goal_description}
Direction: {goal_direction}
Domain: {goal_domain}
Deadline: {deadline_description or "open-ended"}
User-stated metric: {metric_description or "none stated"}
Obstacles noted: {obstacles_noted}
Strategies noted: {strategies_noted}

RULES:
1. Milestones should be observable, concrete checkpoints — not vague ("get healthier")
   but specific enough to recognize when reached ("complete first 5K run").
2. If deadline is known, space milestones across the timeline.
3. If no deadline, create milestones at natural progress points (1/4, 1/2, 3/4, done).
4. Habits should be recurring, small actions that build toward the goal.
5. Generate 2–5 milestones. Generate 1–3 habits.
6. Do NOT generate milestones that require external events outside user control.
7. Keep language grounded in what the user said — do not project ambitions they didn't express.
8. Mark confidence for each: how certain are you this is the right milestone?

Return JSON:
{
  "milestones": [
    {
      "title": "string",
      "description": "string",
      "target_date": null or "ISO date string",
      "progress_weight": 0.0-1.0,  // weights must sum to ~1.0
      "confidence": 0.0-1.0
    }
  ],
  "habits": [
    {
      "title": "string",
      "description": "string",
      "frequency": "daily | weekly | weekdays | custom",
      "target_count_per_period": integer,
      "rationale": "why this habit supports the goal"
    }
  ]
}
```

### 7.4 Post-Decomposition: Layer 6 Handoff

After milestones are created, SC-5 registers each milestone with an upcoming target date into Layer 6's queue:

```python
def register_milestones_with_layer6(goal: Goal) -> None:
    for milestone in goal.milestones:
        if milestone.target_date:
            days_until = (milestone.target_date - datetime.utcnow()).days
            if 0 < days_until <= 90:   # only register milestones in the next 3 months
                create_goal_proactive_item(
                    goal=goal,
                    milestone=milestone,
                    item_type=ProactiveItemType.GOAL_CHECK_IN,
                    earliest_send_time=milestone.target_date - timedelta(days=1),
                    optimal_window=(
                        milestone.target_date - timedelta(days=1),
                        milestone.target_date + timedelta(days=2)
                    ),
                    expiry_time=milestone.target_date + timedelta(days=7)
                )
```

### 7.5 Milestone Completion Detection

When SC-3 detects a `completed` signal for a goal, it also runs a lighter version of the detection logic against individual milestones to check if a milestone (rather than the full goal) has been completed:

```python
def check_milestone_completion(
    goal: Goal,
    user_message: str,
    progress_signal: ProgressSignalClassification
) -> Optional[Milestone]:
    pending_milestones = [m for m in goal.milestones
                          if m.status == MilestoneStatus.PENDING]

    for milestone in pending_milestones:
        milestone_embedding = get_embedding(milestone.title + " " + milestone.description)
        message_embedding = get_embedding(user_message)
        similarity = cosine_similarity(milestone_embedding, message_embedding)

        if similarity > 0.70 and progress_signal.signal_type == "progress_positive":
            return milestone  # this milestone was likely just reached

    return None
```

---

## 8. Layer 7 Output Contract

```python
class Layer7Output:
    # Per-message outputs
    goal_context_packet: GoalContextPacket   # always; may have should_reference_goal=False
    new_goals_created: list[str]             # goal IDs; may be empty
    goals_updated: list[str]                 # goal IDs with status/progress changes

    # Async outputs (written after message completes)
    proactive_items_created: list[str]       # item IDs registered in Layer 6
    layer2_uwm_update: Optional[GoalUWMUpdate]  # UWM update if goal status changed significantly

    # Background scan outputs (every 24h)
    stale_goals_updated: list[GoalStateChange]
    milestones_decomposed: list[str]         # goal IDs that had milestones generated

    # Audit
    cycle_timestamp: datetime
    processing_time_ms: int
```

### 8.1 UWM Update Contract

When a goal reaches a significant lifecycle event (created, completed, abandoned, or transitions to `at_risk`), Layer 7 writes a structured update to the Layer 2 User World Model:

```python
class GoalUWMUpdate:
    user_id: str
    event_type: Literal[
        "goal_created", "goal_completed", "goal_abandoned",
        "goal_at_risk", "milestone_reached"
    ]
    goal_id: str
    goal_title: str
    goal_domain: GoalDomain
    summary: str                            # 1–2 sentence summary for UWM
    emotional_significance: float           # 0.0-1.0; how important is this to the user?
    timestamp: datetime
```

---

## 9. Cross-Layer Contracts

### 9.1 Layer 7 → Layer 4 (GoalContextPacket)

Injected into Layer 4's response generation prompt as an additional section:

```
─── GOAL CONTEXT (Layer 7) ─────────────────────────────────────────────
{response_instruction}
Tone: {tone_instruction}
Reference position: {goal_reference_position}
Max length for goal reference: {max_goal_reference_chars} characters

HARD RULES:
- Do NOT mention the goal system, trackers, or scores
- Do NOT reference more than one goal
- If reference_type is "none", do NOT reference any goal
─────────────────────────────────────────────────────────────────────────
```

### 9.2 Layer 7 → Layer 6 (ProactiveItems)

Layer 7 creates `ProactiveItem` entries using the intake contracts defined in Layer 6 Section 9.4. The item types used are:
- `GOAL_CHECK_IN` — milestone approaching
- `GOAL_ENCOURAGEMENT` — goal is AT_RISK; stale
- `GOAL_CELEBRATION` — goal just completed

### 9.3 Layer 7 → Layer 2 (Memory)

1. **New goal created** → episodic memory event logged: "User stated intention to [goal_title]"
2. **Goal completed** → high-importance episodic memory: "User completed their goal: [goal_title]"
3. **Goal abandoned** → episodic memory: "User abandoned goal: [goal_title]"
4. **UWM update** → `user_world_model.goals_active` list updated

---

## 10. Error Handling and Fallbacks

| Failure Case | Fallback |
|---|---|
| SC-1 LLM extraction times out | Skip extraction for this message; re-queue for post-session inference |
| Goal store read fails | Return empty relevant_goals; no goal reference in response |
| Progress signal classification returns conflict (both positive and negative) | Default to no signal; log conflict for review |
| SC-5 decomposition LLM fails | Leave milestones empty; retry decomposition after next session |
| Layer 6 handoff fails | Log failure; retry on next 24h scan |
| Post-session inference LLM fails | Skip; mark session as "not goal-reviewed"; retry next session |
| Staleness scan fails | Log; retry in 4 hours |
| Duplicate detection embedding unavailable | Skip deduplication; create goal; log collision risk |

**Hard rule:** A failure in any Layer 7 component must never block response generation. All Layer 7 processing that is not on the synchronous read path (SC-2 + SC-4) is asynchronous and failure-tolerant. SC-2 failing returns empty packet; SC-4 with empty packet produces `should_reference_goal = False`.

---

## 11. Design Principles

1. **Goals are inferred, never solicited.** Nova never asks the user to enter a goal. It listens for them. This is the architectural commitment that separates Layer 7 from every productivity app — the user does not interact with a system; they talk to a companion who happens to remember what matters to them.

2. **Progress is narrated, never scored.** Progress scores exist internally for ranking and inference. They are never shown to the user numerically. A user's goal is not a percentage — it is a lived experience, and Nova references it as such.

3. **Goals compete with the conversation, not with each other.** If the current conversation is emotionally important, goals are suppressed entirely. A goal is a long-term signal. The present moment is always higher priority. Layer 7 yields to Layer 3 (emotional state) and Layer 5 (social context) whenever conflict arises.

4. **Accountability is never pressure.** The word "accountability" in the layer name refers to Nova holding the thread of a user's intention across time — not applying pressure, not delivering reminders, not shaming setbacks. A companion says "I remember you wanted this" — not "you haven't done this in 14 days."

5. **Abandonment is valid data.** When a user abandons a goal, Layer 7 does not resist or re-surface it. Abandonment is a signal that the goal may have changed, not that the user failed. The goal is archived with its full history. If the user returns to it, that history is available. If they don't, it is not mentioned again.

---

## 12.5 Implementation Notes (as-built)

This section records how the specification above is realized in `backend/layer7_goals/`. The code is the single source of truth; §1–11 are the design intent.

### Module map

| Spec sub-component | Module | Key entry point |
|---|---|---|
| SC-1 Goal Extractor | `goal_extractor.py` | `should_run_extractor`, `extract_goal`, `is_duplicate_goal`, `GOAL_SIGNAL_KEYWORDS` |
| SC-2 Goal Store | `goal_store.py` | `GoalStore`, `apply_transition`, `STATUS_TRANSITIONS` |
| SC-3 Progress Monitor | `progress_monitor.py` | `classify_progress_signal`, `update_progress_score`, `compute_momentum`, `run_staleness_scan` |
| SC-4 Accountability Response Modifier | `accountability_modifier.py` | `decide_goal_reference` → `GoalContextPacket` |
| SC-5 Goal Decomposer | `goal_decomposer.py` | `decompose_goal`, `register_milestones_with_layer6`, `check_milestone_completion` |
| Orchestrator (§8) | `engine.py` | `run_goal_pipeline` → `Layer7Output` |
| All dataclasses / enums | `schemas.py` | — |

### Type reuse and dependency direction

Layer 7 imports `EmotionClassification` from Layer 3 (the `emotional_state` used in SC-4's distress check). The SC-5 Layer 6 handoff imports Layer 6's `on_goal_milestone_approaching` intake contract and returns Layer 6 `ProactiveItem`s — closing the loop the Proactive Engine already consumes (§9.4 there). There is no forward dependency cycle: Layer 6's intake takes plain goal fields, and Layer 7 calls it.

### Dependency injection for offline testability

The three LLM uses are injected: SC-1 extraction (`llm_fn` returning a dict/JSON), SC-3 post-session deep inference (an LLM call wired by the pipeline; the inline path is keyword-only and never blocks), and SC-5 decomposition (`llm_fn`). The embedding comparisons — dedup (SC-1), relevance (SC-2), milestone matching (SC-5) — accept an injected `similarity_fn` with a token-overlap default. With nothing injected the layer degrades exactly as §10 prescribes: SC-1 returns "no goal," SC-5 returns empty milestones, and the synchronous path still produces a valid (empty) `GoalContextPacket`.

### Behavioral deviations from the design text

- **Lifecycle folded into the Goal Store.** The doc lists SC-2 as "Goal Store" with lifecycle management; the explicit `STATUS_TRANSITIONS` table and `apply_transition` live in `goal_store.py` rather than a separate lifecycle module. The §4.6 table and the §5.6 staleness reasons use different trigger names (`stale_21_days` vs `stale_14_days`); both are encoded, and the 24-hour scan emits `stale_14_days` for active/on-track goals as §5.6 specifies.
- **Extraction inline only with an LLM.** §2 runs SC-1 asynchronously; the orchestrator runs it inline only when an `extractor_llm_fn` is supplied, and always failure-tolerantly (wrapped in `_safe`), so the synchronous response path is never blocked (§10).
- **Scaffold relocation.** The May-28 scaffold (`goal_lifecycle`, `task_engine`, `conflict_detector`, `life_event_tracker`) was removed. Lifecycle is in the store; task plans, goal-conflict detection, and life-event cascades are out of scope for the Layer 7 spec (the doc's five SCs do not include them).

### Hard rules as implemented (§10, §11)

- The synchronous path is wrapped so SC-2 failing returns `[]` and SC-4 then yields `should_reference_goal=False` — a Layer 7 failure never blocks the response.
- Goals yield to the present moment: `decide_goal_reference` hard-blocks crisis / emotional_support / casual modes and brand-new relationships, and only ever references the single highest-relevance goal (§6.4).
- Progress scores are internal only — `GoalContextPacket` carries plain-language `response_instruction` / `tone_instruction`, never a numeric score for the user (§11 principle 2).

### Test coverage

58 unit tests across six files exercise every sub-component and the orchestrator:
`test_goal_extractor.py` (10), `test_goal_store.py` (8), `test_progress_monitor.py` (17), `test_accountability_modifier.py` (11), `test_goal_decomposer.py` (6), `test_layer7_engine.py` (6). Coverage includes the pre-filter + dedup + update/extract branches; the status-transition table and relevance ranking with the at-risk bonus; signal classification, the progress/momentum formulas, and the staleness scan; all four reference cases plus the hard blocks and single-goal rule; decomposition + Layer 6 handoff + milestone-completion detection; and the §10 never-block guarantee.

---

## 12. Performance Targets

| Operation | Target | Notes |
|---|---|---|
| SC-2 goal retrieval (per message) | < 20ms | Indexed query; no LLM |
| SC-3 inline progress signal detection | < 5ms | Keyword matching; no LLM |
| SC-4 packet construction | < 10ms | Deterministic; uses SC-2 + SC-3 results |
| Total synchronous Layer 7 path | < 35ms | Never blocks response generation |
| SC-1 LLM extraction (async) | < 800ms | Runs in background; no user-facing impact |
| SC-3 post-session deep inference (async) | < 1200ms | Runs after session close |
| SC-5 decomposition LLM (async) | < 1500ms | Triggered once on goal activation |
| 24h staleness scan (background) | < 200ms | All users; batch operation |

---

## 13. Live wiring status (Phase 7 polish pass, 2026-08-04)

`backend/layer7_goals/` itself is clean: all 58 tests pass, matches the spec closely (including
the documented §12.5 deviations). Layer 7 is the best-wired layer audited so far — `run_goal_pipeline`
(SC-1 extraction, SC-2 retrieval, SC-3 inline progress inference, SC-4 accountability decision) runs
for real every turn via `make_goal_writer`. One real bug was found and fixed; two structural gaps
were found and logged.

### 13.1 Fixed this phase — `_goal_directive` ignored §6.3's hard blocks

`api/assembly.py`'s `_goal_directive` (which actually reaches the planner prompt — see §13.2)
built its own goal-accountability directive independently of the real `decide_goal_reference`,
and had none of §6.3's hard blocks: it injected a goal reference regardless of
`conversation_mode` (including `crisis` and `emotional_support`, which §6.3 and §6.4 anti-pattern
4 explicitly forbid — "Human distress overrides everything") and regardless of relationship stage
(including brand-new relationships, also explicitly blocked). It also referenced up to 3 goals,
violating anti-pattern 3 ("never reference more than one goal per response").

Fixed by adding the three doc-specified blocks directly to `_goal_directive` and capping to the
single highest-relevance goal title. Verified with a new end-to-end test
(`test_real_layer7_goal_directive_blocked_in_emotional_support_and_shown_in_goal_planning`) that
runs the real orchestrator through blocked-mode, blocked-stage, and allowed cases.

**Practical effect worth stating plainly**: `conversation_mode` defaults to `casual` for most
short/neutral turns (Phase 3 finding), and `casual` is one of the three blocked modes — so this
fix makes goal-accountability injection fire far less often than before (previously: every turn
with an active goal, unconditionally). This is the architecturally correct behavior per §6.3, but
it means the feature is now much quieter in practice than CLAUDE.md previously implied.

### 13.2 Not fixed, tracked in `docs/POLISH_BACKLOG.md`

- **The real `GoalContextPacket` (SC-4's actual output) never reaches Layer 4.**
  `make_goal_writer` calls `run_goal_pipeline` and discards the returned `Layer7Output` entirely
  — every field SC-4 exists to produce (`reference_type`, `response_instruction`,
  `tone_instruction`, `goal_reference_position`, `max_goal_reference_chars`) is computed *after*
  the response has already been delivered, because `make_goal_writer` runs in the post-turn write
  chain (Layer 2 is read-only during inference, by design). `_goal_directive`'s hand-rolled
  directive (§13.1) is what actually reaches the prompt. Reconciling this needs SC-2/3/4 to run
  pre-generation for the current turn, which is a structural pipeline-ordering question, not a
  small fix.
- **SC-5 (Goal Decomposer) never runs; `Goal.milestones` is always `[]` and `Goal.deadline` is
  never populated from extraction.** `engine.py`'s `Goal(...)` construction does not set
  `deadline` from the extractor's `deadline_description`/`has_explicit_deadline` fields (and the
  extractor itself only returns a free-text description, never a parsed date — date parsing from
  natural language isn't implemented anywhere in the codebase). Combined with SC-5 being unwired,
  every extracted goal has no deadline and no milestones. **This corrects a Phase 6 claim**: Layer
  6's `api/proactive_gen.py::goal_checkin_item` was documented as "the one live intake contract"
  producing real candidates, but `_nearest_future_target` requires either a milestone or a
  deadline date to find anything — so for goals extracted through the live pipeline, it returns
  `None` on every turn. The goal→proactive intake is wired correctly; it just has no real input to
  act on yet.

## 14. SC-5 wired + the deadline/metric field-drop fixed (follow-up, 2026-08-09)

Both §13.2 gaps closed, without needing natural-language date parsing:

- **`engine.py`'s `Goal(...)` construction now threads `deadline_description`,
  `deadline_is_inferred` (`not has_explicit_deadline`), `has_metric`, and `metric_description`
  from the extractor's already-computed fields** — they were extracted and simply dropped at
  construction. Proven by `tests/unit/test_layer7_engine.py::
  test_new_goal_threads_deadline_and_metric_fields_from_extraction`. `Goal.deadline` (a parsed
  `datetime`) is still never populated — no natural-language date parser exists anywhere in this
  codebase, and building one is out of scope for a wiring pass — but `deadline_description` now
  reaching the goal also makes SC-5's decomposition prompt (`build_decomposition_prompt`, which
  reads `goal.deadline_description`) actually see the user's stated deadline instead of always
  "open-ended."
- **SC-5 (`decompose_goal`) is now called from `api/state.py::make_goal_writer`** for every goal
  `run_goal_pipeline` newly creates this turn: the goal is reloaded from the store, decomposed via
  an LLM call (JSON milestones with `target_date`/`progress_weight` + habits, per
  `build_decomposition_prompt`), and `goal.milestones`/`goal.habits` are persisted back.
  `decompose_goal`'s own `_parse_date` already accepts an ISO `target_date` string from the LLM —
  no separate date-parsing component was needed, since the decomposition LLM call can be asked to
  return an ISO date directly (unlike the free-text `deadline_description` from the *extraction*
  call, which SC-1's prompt never asked to be structured).
- **Found in the process, fixed as a one-line schema bug**: `Goal.milestones`/`Goal.habits` were
  declared as bare `list` (with a `# list[Milestone]` comment) rather than `list[Milestone]`. The
  shared `infra/db/memory_serde.from_jsonable` reconstructs nested dataclasses only from a real
  parameterized generic — with the bare annotation, a reloaded goal's milestones silently
  round-tripped as plain `dict`s instead of `Milestone` objects, which `goal_checkin_item`'s
  `getattr(ms, "target_date", None)` would have silently read as `None` on every dict (the
  fallback default hides the mismatch instead of raising). Fixed to `list[Milestone]`/
  `list[Habit]` — `Goal.signal_events` on the very next line already used the correct pattern, so
  this was an isolated oversight, not a systemic one.

Proven end to end (extraction → decomposition → persisted `Milestone.target_date` → Layer 6's
`goal_checkin_item` builds a real item) by
`tests/unit/api/test_state.py::test_goal_writer_decomposes_a_new_goal_into_a_dated_milestone`.
This closes the Layer 6 correction noted in §13.2 and `docs/POLISH_BACKLOG.md`'s Layer 6 entry —
`goal_checkin_item` can now produce real candidates for goals the decomposition LLM gives a dated
milestone to. `Layer7Output.milestones_decomposed` (a summary/audit field) is not populated by
this pass — cosmetic, not load-bearing, left as `[]`. `register_milestones_with_layer6` (an
alternate, earlier Layer-6-handoff path, distinct from `goal_checkin_item`'s independent per-turn
walk) remains uncalled — redundant with `goal_checkin_item`, which already covers the same
milestones every turn via `make_proactive_writer`; not wired to avoid two divergent paths writing
the same `GOAL_CHECK_IN` item.

## 15. Goals never actually reached a terminal status (follow-up, 2026-08-09)

Discovered while fixing the `"achieved"` vs. `"completed"` status-string bug flagged as a Layer 10
follow-up (`docs/layer-10-architecture.md` §16.2, §16.6): the real bug was one level deeper than a
string mismatch. **No code in the live per-turn path ever set `Goal.status` to `"completed"` or
`"abandoned"` at all.**

`progress_monitor.update_progress_score` sets `progress_score = 1.0` on a `COMPLETED` signal but
deliberately leaves `.status` untouched — its own comment says "status handled by the transition
rules." But `run_goal_pipeline` (`engine.py`), the only live caller of `update_progress_score`,
never applied any such rule; it just persisted the goal with the score updated and the status
exactly as it was before (almost always `"active"`). A user saying "I finally finished my
marathon goal!" would move `progress_score` to 1.0 and trigger a `CELEBRATE_COMPLETION` reference
that same turn, but the goal itself stayed `status="active"` forever afterward, with `status_
changed_at` never existing as a field to set in the first place. This was invisible to the
existing test (`test_completion_celebrated_and_score_full`) because it only ever asserted on
`progress_score`, never on `status`.

**Fixed**: `Goal` gained a `status_changed_at: Optional[datetime]` field (set at creation too, for
consistency — a goal's status did "change" to `active` the moment it was created).
`run_goal_pipeline` now transitions `top.status` to `"completed"`/`"abandoned"` and stamps `status_
changed_at` when `progress_signal.signal_type` is one of those two terminal values (their string
values already match `GoalStatus`'s 1:1, so no new mapping was needed). Proven by two new tests
in `tests/unit/test_layer7_engine.py`
(`test_completion_signal_transitions_status_and_stamps_status_changed_at`,
`test_abandonment_signal_transitions_status`) that assert on `.status`/`.status_changed_at`
directly, closing the exact blind spot the old test had.

This also fixes the actual root cause of `docs/layer-10-architecture.md` §16.6's Year in Review
gap — `generate_year_in_review`'s `"achieved"` string (now fixed to `"completed"` in both
`backend/layer10_longitudinal/retrospective.py` and `progress_tracker.py`) had nothing to match
against anyway, since no goal ever reached that status. Both problems needed fixing together;
fixing only the string would have left `achieved`/`goals_achieved` at 0 regardless.

**Still open — found but not fixed this pass, logged properly rather than patched inline**:
`progress_monitor.run_staleness_scan` (§5.6 — the staleness-driven decay path: `TENTATIVE`→
`ARCHIVED` after 30 days untouched, `ACTIVE`/`ON_TRACK`→`AT_RISK` after 14 days, `AT_RISK`→
`ABANDONED` after 30 more) **has zero production callers** (`grep -rn "run_staleness_scan"` outside
`backend/layer7_goals/` and its own tests returns nothing). This is a real, previously-undocumented
gap: without it, a goal the user simply stops mentioning never decays status on its own — it can
only reach a terminal state through an explicit completion/abandonment phrase (now fixed above).
Wiring it needs a background-job-shaped caller (a periodic sweep over all active goals, the same
shape as `pattern_detection_job.py`/`life_calendar_job.py`), which is real, separate feature work —
not something to fold silently into this fix. Tracked in `docs/POLISH_BACKLOG.md`.

## 16. Follow-up (2026-08-09): `run_staleness_scan` wired + SC-4 reaches Layer 4 pre-generation

### 16.1 Goal staleness sweep

§15's "found but not fixed" gap is closed: `background/goal_staleness_job.py` (new, weekly) loads
every goal in `tentative`/`active`/`on_track`/`at_risk` status, runs the real
`run_staleness_scan`, and applies each `GoalStateChange` (status + `status_changed_at`) back
through the real `PostgresGoalStore`. Registered in `background/scheduler.py`'s `JOBS` (weekly
cadence, `goal_staleness_days` config key, default 7). Tests:
`tests/unit/background/test_jobs.py::test_goal_staleness_job_decays_a_silently_neglected_active_
goal` (a goal untouched for 20 days transitions to `at_risk` and persists for real) and
`..._leaves_recently_mentioned_goals_untouched`.

### 16.2 SC-4's `GoalContextPacket` now reaches Layer 4, same-turn

§13's pending item ("SC-4's real `GoalContextPacket` still never reaches Layer 4 — a
pipeline-ordering question") turned out to have a cleaner resolution than persisting-and-
replaying a stale decision across turns. `decide_goal_reference` (`accountability_modifier.py`)
is pure and read-only — it was only ever called from *inside* `run_goal_pipeline`
(`make_goal_writer`, post-turn) because that's where SC-1/SC-2/SC-3 happen to run, not because it
needs to. `classify_progress_signal` (the only other input it depends on besides a read-only
`get_relevant_goals` query) is equally pure — the *mutating* half of progress classification
(`update_progress_score`, `goal_store.update_goal`) is a separate call the writer still owns.

`api/state.py::make_goal_provider` now calls `get_relevant_goals` → `classify_progress_signal` →
`decide_goal_reference` directly, pre-generation, with this turn's *live* `conversation_mode`/
`emotional_state`/`relationship_stage` — not a persisted decision from last turn. This matters
because "goals yield to the present moment" (§11 principle 3) is a same-turn invariant: a
persist-and-replay approach would have referenced a goal using a stale gate decision computed
under last turn's mode, wrong exactly on the turns where the mode changed (e.g. casual → crisis).

`api/assembly.py::_goal_directive` was rewritten to consume the real `GoalContextPacket`
(`response_instruction`) instead of a bare-titles list, and its duplicated `_GOAL_BLOCKED_MODES`/
stage check was deleted — `decide_goal_reference` already enforces the same §6.3 hard rule
internally, so duplicating it was exactly the drift-risk CLAUDE.md warns about (a rule fixed in
one place silently unfixed in the other). The directive text is now real and
progress-signal-differentiated (celebratory on completion, gentle on a distressed setback, a
one-sentence topic connection when relevant) instead of one generic "reference it naturally"
template — reaching the planner via `_goal_directive`'s existing call site, no new hook.

**Test rewrite required**: the pre-existing tests passed `goal_provider=lambda uid, msg: ["Run a
5K"]` — bare title strings, incompatible with `decide_goal_reference`'s real `RelevantGoal`/`Goal`
inputs (its topic-connection case specifically needs a real `Goal.momentum_score`). Rewrote
`tests/unit/api/test_assembly_turn.py::test_real_layer7_goal_directive_blocked_in_emotional_
support_and_shown_in_goal_planning` and `tests/unit/api/test_goal_relationship_injection.py::
test_goal_titles_injected_into_prompt` to seed a real persisted `Goal` through `PostgresGoalStore`
and trigger a real completion-signal case, rather than a synthetic list.

*This document specifies Layer 7 completely. All five sub-components have full schemas, all algorithms are specified with exact logic, and all gaps from prior documents — goal extraction with LLM prompt and deduplication, Goal Store with full 12-field schema including milestones/habits, progress scoring formula and momentum metric, decision logic for all four reference types, goal decomposition with full prompt, Layer 6 milestone handoff, Layer 2 UWM contract, and cross-layer output contracts — are fully resolved. No behavior of Layer 7 requires assumptions or inference from other documents.*
