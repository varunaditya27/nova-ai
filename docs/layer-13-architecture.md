# Layer 13 — Onboarding & Cold Start Architecture
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

Every other layer in NovaAI operates with context — memories to draw on, a personality vector shaped by experience, a narrative arc being constructed, patterns detected across weeks of interaction. Layer 13 is the exception. It is the only moment in the entire system where Nova has nothing: no episodic memories, no semantic facts, no longitudinal data, no personality drift history, no emotional baseline calibrated to this person.

The memory stores are empty databases. The personality vector is set to population defaults. The emotional baseline is flat.

This is the cold start problem, and in the context of a deeply personal AI companion, it is uniquely high-stakes. The cold start problem in recommendation systems is an optimization problem — you get slightly worse recommendations for a while. In NovaAI, it is an experiential problem: **the first session shapes whether a person ever trusts Nova enough to let it become what it is capable of being.** Get the first conversation wrong and no amount of sophistication in Layers 1–12 will save it — the user will have already decided this is not for them.

Layer 13 is not just the first impression. It is the system that manages the entire onboarding arc from the first message to the moment when the cold start period ends and the full system comes online. It is responsible for three things:

- **SC-1: Progressive Elicitation** — how Nova learns about the user without interrogating them
- **SC-2: Cold Start Handling** — how the system initializes, what defaults it uses, and how it builds context in real-time from nothing
- **SC-3: Feature Introduction Pacing** — how and when capabilities are introduced so each one lands as a discovery, not a surprise

These three sub-components are coordinated by a **Cold Start Engine** that acts as a temporary overlay on the normal conversation pipeline, adding constraints and context-building operations until graduation criteria are met, then self-terminating.

---

## 2. Three Design Principles

All architecture decisions in Layer 13 follow three governing principles. These are not aspirational — they are enforceable constraints reflected in the data structures and algorithms below.

**Earn before asking.** The worst cold start experience is an intake form wearing a chatbot disguise. If the first thing Nova does is ask for the user's name, age, location, occupation, goals, personality type, and communication preferences — even wrapped in friendly language — it feels like paperwork. It signals that Nova needs data before it can function, which is the opposite of how a real relationship starts. Nova earns each piece of information by first demonstrating it is worth sharing with.

**Infer before asking.** Much of what Nova needs to know can be observed rather than asked. The user's vocabulary, sentence complexity, and topic choices in their first three messages reveal more about their communication style than any questionnaire. The user's emotional register in the first session sets the baseline. The time of day, the first topic raised, whether they dive in or hang back — all of these are data. Nova reads before it speaks, not asks before it listens.

**Delay features, not presence.** The cold start period does not mean Nova should feel limited or incomplete. It should feel fully present from the first message — warm, attentive, genuinely responsive — while the complex machinery of longitudinal tracking, pattern detection, and life narrative construction quietly begins its work in the background. The user does not need to know that Layer 10 will generate a Weekly Summary in seven days. They need to feel, from the first exchange, that this companion is worth returning to.

---

## 3. Architecture Overview

```
New User — First Message
       │
       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Cold Start Engine (temporary overlay — active from T=0 until graduation)  │
│                                                                            │
│  ┌──────────────────────┐   ┌──────────────────────┐                      │
│  │  SC-1                │   │  SC-2                │                      │
│  │  Progressive         │   │  Cold Start          │                      │
│  │  Elicitation         │   │  Handling            │                      │
│  │  ├─ ElicitationQueue │   │  ├─ InitialState      │                      │
│  │  ├─ PassiveEngine    │   │  ├─ ColdStartConfig   │                      │
│  │  └─ SurfacingPolicy  │   │  └─ ContextBuilder   │                      │
│  └────────┬─────────────┘   └──────────┬───────────┘                      │
│           │                            │                                   │
│           └────────────────┬───────────┘                                   │
│                            │                                               │
│                  ┌─────────▼─────────┐                                    │
│                  │  GraduationEval   │                                    │
│                  │  (checked at end  │                                    │
│                  │  of each session) │                                    │
│                  └─────────┬─────────┘                                    │
│                            │                                               │
│  ┌─────────────────────────▼────────────────────────┐                     │
│  │  SC-3: Feature Introduction Pacing               │                     │
│  │  FeaturePacingController — gates all features     │                     │
│  │  until their FeatureReadinessProfile is met       │                     │
│  └─────────────────────────┬────────────────────────┘                     │
│                            │                                               │
└────────────────────────────┼───────────────────────────────────────────────┘
                             │ Cold Start Engine self-terminates on graduation
                             ▼
               Normal Runtime (Layers 1–12 fully active)
               Conversation Orchestrator takes full control
```

---

## 4. Sub-Component 1 — Progressive Elicitation

### 4.1 What Progressive Elicitation Is

Progressive elicitation is the systematic, non-intrusive process of learning about the user through naturally timed questions and passive observation spread across sessions — never front-loaded into the first experience. It is the architectural answer to: *how does Nova go from knowing nothing to knowing enough to be genuinely personal, without feeling like an interrogation?*

Two modes operate simultaneously:

- **Active elicitation** — questions Nova deliberately chooses to ask, because the answer would meaningfully improve understanding. Embedded naturally in conversation, never presented as forms, never in a predetermined sequence.
- **Passive elicitation** — learning through observation. Every message the user sends contains information Nova can extract without asking: emotional register, vocabulary sophistication, communication style, topics drawn to, topics avoided, how they handle uncertainty, whether they self-disclose or stay reserved.

### 4.2 Elicitation Queue Schema

```python
class ElicitationItem:
    item_id: UUID
    category: Literal[
        "identity",             # name/handle; how they want to be addressed
        "life_context",         # student/working/other; broad life situation
        "communication_pref",   # verbosity preference, formality level
        "goals",                # what they hope to get from Nova
        "relationships",        # close people in their life
        "values",               # things they care about
        "emotional_style",      # how they process and express feelings
        "reason_for_use",       # why they started using Nova
    ]
    question: str               # the actual question Nova might ask (exact wording)
    inference_target: str       # what filling this answer populates in InitialState
    priority: int               # 1=critical, 2=important, 3=nice-to-have
    prerequisite_item_ids: list[UUID]   # items that should be answered before this one
    can_infer_without_asking: bool      # can passive elicitation fill this?
    natural_triggers: list[str] # conversation contexts that make this question feel natural
    status: Literal["waiting", "surfaced", "answered", "inferred", "expired"]
    surfaced_at_session: Optional[int]  # session number when question was asked
    answered_at_session: Optional[int]
    inferred_value: Optional[str]       # value populated by passive inference

class ElicitationQueue:
    user_id: str
    items: list[ElicitationItem]        # priority-sorted; NEVER asked in sequence

    def next_surfaceable_item(
        self,
        session_context: SessionContext,
        current_session_number: int,
        emotional_intensity: float,
        topic_in_progress: Optional[str],
    ) -> Optional[ElicitationItem]:
        """
        Return the highest-priority item whose natural trigger has fired,
        whose prerequisites are met, and whose category is emotionally appropriate.
        Returns None if no item is ready to surface this session.
        """
        for item in sorted(self.items, key=lambda i: i.priority):
            if item.status != "waiting":
                continue
            # Check prerequisites
            prereqs_met = all(
                self._is_answered_or_inferred(prereq_id)
                for prereq_id in item.prerequisite_item_ids
            )
            if not prereqs_met:
                continue
            # Check natural trigger
            trigger_fired = any(
                trigger in (topic_in_progress or "")
                for trigger in item.natural_triggers
            )
            if not trigger_fired:
                continue
            # Check emotional register appropriateness
            if emotional_intensity > 0.60 and item.priority == 3:
                continue    # never surface nice-to-have during emotionally heavy sessions
            return item
        return None
```

### 4.3 Initial Elicitation Queue — Population at Initialization

```python
INITIAL_ELICITATION_ITEMS = [

    # ── PRIORITY 1: CRITICAL ──────────────────────────────────────────────────

    ElicitationItem(
        category="identity",
        question="Hey — what should I call you?",
        inference_target="user_handle",
        priority=1,
        prerequisite_item_ids=[],
        can_infer_without_asking=False,     # cannot be inferred — must be asked or given
        natural_triggers=[
            "any_first_personal_address_moment",
            "user_says_hi_or_hello",
            "end_of_first_exchange",
        ],
        # Surfacing rule: only if user has not introduced themselves in the first message.
    ),

    ElicitationItem(
        category="life_context",
        question="Are you a student, or are you working? Or something else entirely?",
        inference_target="life_phase",
        priority=1,
        prerequisite_item_ids=[],           # no prerequisites
        can_infer_without_asking=True,      # mentions of exams, work, campus, office
        natural_triggers=[
            "user_mentions_exams_or_studying",
            "user_mentions_work_or_job",
            "user_mentions_a_schedule",
            "user_asks_about_productivity",
            "user_mentions_stress",
        ],
    ),

    # ── PRIORITY 2: IMPORTANT ─────────────────────────────────────────────────

    ElicitationItem(
        category="communication_pref",
        question=None,  # inferred only; never directly asked
        inference_target="verbosity_preference",
        priority=2,
        prerequisite_item_ids=[],
        can_infer_without_asking=True,      # passively inferred from message length patterns
        natural_triggers=[],                # passive only; no active surfacing
    ),

    ElicitationItem(
        category="reason_for_use",
        question="What made you want to try this?",
        inference_target="primary_reason",
        priority=2,
        prerequisite_item_ids=[],
        can_infer_without_asking=False,
        natural_triggers=[
            "session_2_or_3_any_reflective_moment",
            "user_says_something_about_wanting_to_change",
            "user_mentions_loneliness_or_isolation",
            "user_mentions_needing_someone_to_talk_to",
        ],
    ),

    ElicitationItem(
        category="relationships",
        question=None,  # inferred from names mentioned
        inference_target="close_relationships",
        priority=2,
        prerequisite_item_ids=[],
        can_infer_without_asking=True,      # names that appear in conversations
        natural_triggers=[],                # passive only
    ),

    # ── PRIORITY 3: NICE-TO-HAVE ──────────────────────────────────────────────

    ElicitationItem(
        category="goals",
        question="Is there something you've been working toward lately?",
        inference_target="primary_goal_area",
        priority=3,
        prerequisite_item_ids=[],
        can_infer_without_asking=True,      # partially — if they bring up ambitions
        natural_triggers=[
            "user_mentions_wanting_to_do_something",
            "user_mentions_a_plan",
            "user_asks_for_advice_about_direction",
        ],
    ),

    ElicitationItem(
        category="emotional_style",
        question=None,  # inferred from emotional expression patterns
        inference_target="emotional_expression_style",
        priority=3,
        prerequisite_item_ids=[],
        can_infer_without_asking=True,
        natural_triggers=[],                # passive only
    ),

    ElicitationItem(
        category="values",
        question=None,  # inferred from what they express care about
        inference_target="core_values_sketch",
        priority=3,
        prerequisite_item_ids=[],
        can_infer_without_asking=True,
        natural_triggers=[],                # passive only
    ),
]
```

### 4.4 The Three Surfacing Rules

An elicitation item never surfaces unless **all three conditions are met simultaneously**:

```python
class ElicitationSurfacingPolicy:

    EARLY_PERIOD_SESSIONS = 14   # first two weeks
    MAX_ELICITATION_PER_SESSION = 1  # hard rate limit in early period

    def can_surface(
        self,
        item: ElicitationItem,
        session_context: SessionContext,
        current_session_number: int,
        emotional_intensity: float,
        elicitation_count_this_session: int,
    ) -> bool:
        """
        All three conditions must be true simultaneously.
        """

        # CONDITION 1: The topic has naturally arisen in conversation
        # Nova never asks "what do you do for work?" out of nowhere.
        # It asks "sounds like a demanding schedule — are you a student or working?"
        # when the user mentions exams or work stress.
        # The question must feel like a natural next sentence, not a segue to a form.
        trigger_active = item.status == "waiting" and session_context.active_triggers.intersection(
            set(item.natural_triggers)
        )
        if not trigger_active:
            return False

        # CONDITION 2: Emotional register is appropriate for this item's priority
        # Priority-3 (nice-to-have) items NEVER surface during emotionally heavy sessions.
        # "So, what are your long-term goals?" when the user is venting is a violation.
        if emotional_intensity > 0.60 and item.priority >= 3:
            return False
        # Priority-2 items are suppressed during acute distress
        if emotional_intensity > 0.80 and item.priority >= 2:
            return False

        # CONDITION 3: Elicitation rate limit — maximum one active elicitation
        # question per session in the first two weeks
        if (current_session_number <= self.EARLY_PERIOD_SESSIONS and
                elicitation_count_this_session >= self.MAX_ELICITATION_PER_SESSION):
            return False

        # All conditions met
        return True
```

### 4.5 Passive Elicitation Engine

```python
class PassiveElicitationEngine:
    """
    Runs on every incoming message from the first message onward.
    Extracts context signals without asking the user anything.
    Updates InitialState in real-time.
    """

    def extract(
        self,
        message: str,
        message_index: int,
        session_number: int,
        timestamp: datetime,
        session_history: list[MessageTurn],
    ) -> PassiveSignalBundle:
        """
        Run all extractors in parallel and return extracted signals.
        """
        return PassiveSignalBundle(
            vocabulary_register=self._extract_vocabulary_register(message),
            emotional_expression_style=self._extract_emotional_style(message, session_history),
            topic_approach=self._extract_topic_approach(message, session_history),
            self_disclosure_comfort=self._extract_disclosure_comfort(message, session_history),
            temporal_pattern=self._extract_temporal_pattern(timestamp, session_number),
            named_entities=self._extract_named_people(message),
            life_context_signals=self._extract_life_context(message),
            urgency_signals=self._extract_urgency(message),
            communication_style=self._extract_communication_style(message, session_history),
        )

    # ── EXTRACTOR 1: Vocabulary and Communication Register ─────────────────
    def _extract_vocabulary_register(self, message: str) -> VocabularyRegister:
        """
        Infers: verbosity_preference, formality_level, technical_comfort
        Used by: PersonalityVector (verbosity, formality dimensions)
        """
        words = message.split()
        avg_word_length = sum(len(w) for w in words) / max(len(words), 1)
        sentence_count = len(re.split(r'[.!?]+', message))
        avg_sentence_length = len(words) / max(sentence_count, 1)
        has_emoji = bool(re.search(r'[\U00010000-\U0010ffff]|[\u2600-\u27ff]', message))
        formal_markers = ["therefore", "however", "furthermore", "regarding", "consequently"]
        informal_markers = ["lol", "tbh", "ngl", "kinda", "gonna", "wanna", "idk"]
        formality_score = (
            sum(1 for m in formal_markers if m in message.lower()) -
            sum(1 for m in informal_markers if m in message.lower())
        )
        return VocabularyRegister(
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            uses_emoji=has_emoji,
            formality_delta=formality_score,
            message_length=len(words),
        )

    # ── EXTRACTOR 2: Emotional Expression Style ────────────────────────────
    def _extract_emotional_style(
        self, message: str, history: list[MessageTurn]
    ) -> EmotionalExpressionStyle:
        """
        Infers: direct vs. indirect emotional expression
        Used by: Empathy Hypothesis (Layer 3), Response Refiner calibration
        Direct: "I'm really anxious about this"
        Indirect: "It's just been a weird week"
        """
        DIRECT_EMOTION_WORDS = [
            "anxious", "scared", "angry", "sad", "happy", "excited",
            "frustrated", "overwhelmed", "confused", "proud", "hurt",
        ]
        INDIRECT_HEDGES = [
            "just", "kind of", "sort of", "a bit", "weird", "off",
            "not great", "not bad", "fine I guess",
        ]
        direct_count = sum(1 for w in DIRECT_EMOTION_WORDS if w in message.lower())
        indirect_count = sum(1 for h in INDIRECT_HEDGES if h in message.lower())
        # Compute style across history if available
        if len(history) >= 3:
            historical_direct = sum(
                1 for t in history
                if any(w in t.user_message.lower() for w in DIRECT_EMOTION_WORDS)
            )
            style_confidence = min(len(history) / 10, 1.0)
        else:
            historical_direct = 0
            style_confidence = 0.2
        return EmotionalExpressionStyle(
            style=("direct" if direct_count > indirect_count else "indirect"),
            confidence=style_confidence,
        )

    # ── EXTRACTOR 3: Topic Approach ────────────────────────────────────────
    def _extract_topic_approach(
        self, message: str, history: list[MessageTurn]
    ) -> TopicApproach:
        """
        Infers: context-builder vs. diver; opinion-seeker vs. fact-seeker
        Does the user build context first before stating the problem?
        Do they ask for opinions or facts?
        Do they hedge their own views?
        """
        HEDGING_PHRASES = [
            "I might be wrong", "not sure but", "just my opinion",
            "I think", "maybe", "could be wrong"
        ]
        OPINION_REQUESTS = ["what do you think", "your opinion", "what would you do"]
        FACT_REQUESTS = ["how do I", "what is", "can you explain", "what's the best way"]
        hedging = any(h in message.lower() for h in HEDGING_PHRASES)
        opinion_seeking = any(o in message.lower() for o in OPINION_REQUESTS)
        fact_seeking = any(f in message.lower() for f in FACT_REQUESTS)
        # Context-building: long message with background before the actual question
        context_building = (len(message.split()) > 50 and
                            message.strip().endswith("?"))
        return TopicApproach(
            hedges_views=hedging,
            seeks_opinions=opinion_seeking,
            seeks_facts=fact_seeking,
            context_builder=context_building,
        )

    # ── EXTRACTOR 4: Self-Disclosure Comfort ─────────────────────────────
    def _extract_disclosure_comfort(
        self, message: str, history: list[MessageTurn]
    ) -> DisclosureComfort:
        """
        Infers: how much personal information user shares unsolicited
        High disclosure → high comfort with intimacy; Nova can mirror
        Low disclosure → conservative default; wait for permission signals
        """
        PERSONAL_DISCLOSURE_MARKERS = [
            r"I (am|was|feel|felt|have|had|went|did|said|told|made)",
            r"my (friend|family|mom|dad|sister|brother|partner|job|life|problem)",
            r"(I'm|im) (going through|dealing with|struggling with)",
        ]
        disclosure_signals = sum(
            1 for pattern in PERSONAL_DISCLOSURE_MARKERS
            if re.search(pattern, message, re.IGNORECASE)
        )
        message_word_count = len(message.split())
        # Normalize: disclosure density
        disclosure_density = disclosure_signals / max(message_word_count / 20, 1)
        return DisclosureComfort(
            density=min(disclosure_density, 1.0),
            level=("high" if disclosure_density > 0.3
                   else "medium" if disclosure_density > 0.1
                   else "low"),
        )

    # ── EXTRACTOR 5: Named People ──────────────────────────────────────────
    def _extract_named_people(self, message: str) -> list[NamedPersonSignal]:
        """
        Infers: close relationships
        Detects proper nouns in relational context.
        Seeds Layer 2 semantic memory with relationship stubs.
        """
        # Pattern: "my [relationship_word] [Name]" or "[Name] [relationship_verb]"
        RELATIONSHIP_CONTEXT_PATTERN = re.compile(
            r'(my\s+)?(friend|sister|brother|mom|dad|partner|boyfriend|girlfriend|'
            r'roommate|colleague|professor|boss)\s+([A-Z][a-z]+)',
            re.IGNORECASE,
        )
        STANDALONE_NAME_PATTERN = re.compile(r'([A-Z][a-z]{2,})')

        people = []
        for match in RELATIONSHIP_CONTEXT_PATTERN.finditer(message):
            people.append(NamedPersonSignal(
                name=match.group(3),
                relationship_type=match.group(2).lower(),
                confidence=0.85,
            ))
        return people

    # ── EXTRACTOR 6: Life Context Signals ─────────────────────────────────
    def _extract_life_context(self, message: str) -> LifeContextSignals:
        """
        Infers: life_phase (student/working/other), current major preoccupation
        """
        STUDENT_SIGNALS = ["exam", "class", "semester", "assignment", "campus",
                           "professor", "study", "college", "university", "degree"]
        WORK_SIGNALS = ["work", "job", "office", "meeting", "deadline", "manager",
                        "client", "salary", "career", "company"]
        student_score = sum(1 for s in STUDENT_SIGNALS if s in message.lower())
        work_score = sum(1 for s in WORK_SIGNALS if s in message.lower())
        if student_score > 0 and student_score >= work_score:
            life_phase_signal = "student"
            confidence = min(student_score * 0.3, 0.9)
        elif work_score > 0:
            life_phase_signal = "working"
            confidence = min(work_score * 0.3, 0.9)
        else:
            life_phase_signal = None
            confidence = 0.0
        return LifeContextSignals(
            life_phase_signal=life_phase_signal,
            life_phase_confidence=confidence,
        )

    # ── EXTRACTOR 7: Urgency ───────────────────────────────────────────────
    def _extract_urgency(self, message: str) -> UrgencySignal:
        """
        Infers: whether the user needs something immediately vs. exploring
        """
        HIGH_URGENCY_PATTERNS = [
            "asap", "urgent", "need to know now", "happening right now",
            "tonight", "tomorrow morning", "in an hour",
        ]
        EXPLORATORY_PATTERNS = [
            "just wondering", "curious", "was thinking", "what do you think",
            "no rush", "whenever",
        ]
        urgent = any(p in message.lower() for p in HIGH_URGENCY_PATTERNS)
        exploratory = any(p in message.lower() for p in EXPLORATORY_PATTERNS)
        return UrgencySignal(
            level=("high" if urgent else "low" if exploratory else "medium")
        )

    # ── EXTRACTOR 8: Communication Style (evolves over sessions) ──────────
    def _extract_communication_style(
        self, message: str, history: list[MessageTurn]
    ) -> CommunicationStyleUpdate:
        """
        Infers: verbosity preference (from message length distribution)
        Message length distribution across sessions is the most reliable
        signal for verbosity preference.
        """
        lengths = [len(t.user_message.split()) for t in history] + [len(message.split())]
        avg_length = sum(lengths) / len(lengths)
        return CommunicationStyleUpdate(
            avg_user_message_length=avg_length,
            verbosity_preference=(
                "concise" if avg_length < 20
                else "medium" if avg_length < 60
                else "verbose"
            ),
            sample_count=len(lengths),
        )
```

### 4.6 Elicitation Timeline

```python
ELICITATION_TIMELINE = {
    "phase_1": {
        "sessions": "1",
        "description": "Observe, don't ask.",
        "rules": [
            "The first conversation is almost entirely observational.",
            "Nova is warm and responsive. Asks one follow-up question to show genuine engagement.",
            "Passive elicitation extractors run on every message.",
            "The only active elicitation permitted: the user's name/handle — and only "
            "if it has not naturally come up in their opening message.",
            "The ElicitationQueue surfaces at most 0 items proactively in session 1.",
            "Exception: if the user introduces themselves, that counts as answered.",
        ],
        "passive_extraction_priority": ["vocabulary_register", "emotional_style",
                                         "disclosure_comfort", "life_context_signals", "urgency"],
    },
    "phase_2": {
        "sessions": "2–10",
        "description": "One natural question per session, if triggered.",
        "rules": [
            "Priority-1 and priority-2 items surface one at a time, only when naturally triggered.",
            "Maximum 1 active elicitation question per session. Hard rate limit.",
            "No question ever surfaces unless its natural trigger has fired.",
            "No question surfaces during emotionally heavy sessions (intensity > 0.6).",
            "By session 10, target knowledge: life context, communication preferences, "
            "primary language, reason for using Nova, names of a few people in their life.",
        ],
    },
    "phase_3": {
        "sessions": "11+",
        "description": "Ongoing discovery — no longer queue-driven.",
        "rules": [
            "Elicitation queue continues to be populated from new conversational unknowns.",
            "At this point the system has enough context that most remaining elicitation "
            "happens naturally through rich ongoing conversation.",
            "The queue still governs active elicitation rate limits.",
            "Passive extraction continues for all sessions indefinitely.",
        ],
    },
}
```

---

## 5. Sub-Component 2 — Cold Start Handling

### 5.1 The Initialization State

When a new user opens Nova for the first time, every component of the cognitive architecture is seeded with population defaults — not arbitrary values, but statistically grounded starting points based on what works best for interactions with unknown users.

```python
class InitialState:
    user_id: str
    initialized_at: datetime
    cold_start: bool = True
    cold_start_session_count: int = 0
    cold_start_ends: Optional[datetime] = None  # set when graduation criteria are met

    # Personality Vector — population-center defaults
    personality_vector: PersonalityVector = PersonalityVector(
        warmth=0.75,            # slightly warm — safe default for almost all users
        verbosity=0.45,         # medium-low — let the user set the pace
        humor=0.35,             # present but not leading
        formality=0.40,         # casual but not jarring
        empathy_bias=0.70,      # high — safe default for first impressions
        sarcasm_threshold=0.20, # nearly off — too risky cold
        assertiveness=0.50,     # balanced
        curiosity_expression=0.65,  # slightly high — asking is how you learn
        directness=0.55,        # moderate
    )

    # Emotional Baseline — neutral, slightly warm
    emotional_baseline: EmotionalBaseline = EmotionalBaseline(
        valence=0.15,           # slightly positive
        arousal=0.20,           # calm
        engagement_level=0.60,  # attentive
    )

    # Memory stores — empty but initialized
    episodic_memory: list = field(default_factory=list)
    semantic_memory: list = field(default_factory=list)
    identity_memory: list = field(default_factory=list)

    # Relationship state
    relationship_stage: RelationshipStage = RelationshipStage.NEW_ACQUAINTANCE

    # Context fields — populated progressively
    user_handle: Optional[str] = None
    life_phase: Optional[str] = None           # "student" | "working" | "other"
    communication_style_profile: Optional[CommunicationStyleProfile] = None
    emotional_baseline_calibrated: bool = False
    primary_topic_areas: list[str] = field(default_factory=list)
    primary_reason: Optional[str] = None
    named_relationships: list[NamedPersonSignal] = field(default_factory=list)


class ColdStartBehaviorConfig:
    """
    Behavioral constraints active while cold_start == True.
    Applied as an overlay on the normal system configuration.
    """

    # Memory
    suppress_memory_retrieval_failures: bool = True
    # In normal operation, a retrieval failure → "remind me?" In cold start,
    # there are no prior memories to retrieve, so this behavior is suppressed entirely.

    # Personality vector drift
    personality_drift_gate_multiplier: float = 0.30
    # Normal gate allows faster drift. During cold start, drift is slower
    # (0.30 multiplier) because there is not enough data to confidently update.

    # Proactivity Engine (Layer 6)
    proactivity_mode: Literal["observe_only"] = "observe_only"
    # No check-ins. No pattern-based proactive reaches.
    # The system has not observed enough patterns to act on.

    # Longitudinal Layer (Layer 10)
    longitudinal_mode: Literal["seeded_but_silent"] = "seeded_but_silent"
    # Weekly summary cycle begins on first day of use.
    # Chapter detection, turning point identification only activate after graduation.

    # Relationship stage advancement
    relationship_stage_advance_gate: float = 0.50
    # Normal threshold for stage advancement. During cold start, gate is higher:
    relationship_stage_advance_gate_cold_start: float = 0.75
    # Prevents premature relationship stage escalation based on insufficient data.

    # Elicitation rate
    max_elicitation_per_session: int = 1
    elicitation_embargo_on_emotional_intensity: float = 0.60

    # Layer 11 — Safety is never gated
    safety_layer_active: bool = True
    # Safety and crisis detection are fully operational from message 0.
    # No cold start exemption or gate applies to Layer 11 under any condition.
```

### 5.2 The First Message

```python
FIRST_MESSAGE_DESIGN_REQUIREMENTS = {
    "length": "short — not a wall of text explaining what Nova is",
    "tone": "warm but not cloying",
    "structure": "open-ended invitation, not a funnel into structured intake",
    "question_count": "zero questions OR one gentle invitation — never a list",
    "character": "authentic to Nova's character: thoughtful, present, honest, curious",
}

FIRST_MESSAGE_TEMPLATE = (
    "Hey. I'm Nova — not much to say as an intro, honestly. "
    "The best way to figure out what this is for you is just to start talking. "
    "What's on your mind?"
)
# This message works because:
# - It is genuinely humble: acknowledges Nova doesn't know what it will mean to this person
# - "What's on your mind?" is maximally open: can receive anything from
#   "I want help with my career" to "I just had a terrible day" to "I'm not sure what to say"
# - Short. Does not front-load capabilities or expectations.
# - Warm without being cloying or over-eager.

FIRST_MESSAGE_ANTI_PATTERNS = [
    "Hi! I'm so excited to meet you and help you with all your goals!",
    # → hollow, performative, sets expectations Nova cannot immediately deliver
    "Welcome to Nova! To get started, I'd love to learn a bit about you. What's your name?",
    # → immediately feels like an intake form
    "Hello! I'm Nova, your personal AI companion. I can help you with emotional support, "
    "goal tracking, journaling, and much more!",
    # → feature announcement before relationship; feels like a product pitch
    "Hi there! Could you tell me your name, what you do, and what you're hoping to get from this?",
    # → explicit intake form; violates "earn before asking"
]

def generate_first_message(
    persona_config: PersonaConfig,
    time_of_day: str,         # circadian band from Layer 1
    session_context: SessionContext,
) -> str:
    """
    The Persona Agent shapes the first message template.
    The core content is fixed by the template requirements above.
    Persona only adjusts the precise wording, not the structure.
    """
    # Late night: slightly quieter opener
    if time_of_day == "late_night":
        return (
            "Hey. I'm Nova. It's late — you must have something on your mind. "
            "What's going on?"
        )
    # Standard
    return FIRST_MESSAGE_TEMPLATE
```

### 5.3 Real-Time Context Construction Pipeline

```python
class ColdStartContextBuilder:
    """
    Specialized mode during cold start that processes every message for context signals
    more aggressively than normal operation.
    Runs in parallel with the normal conversation pipeline.
    Feeds extracted signals into InitialState immediately.
    """

    def process_message(
        self,
        message: str,
        message_index: int,
        session_number: int,
        timestamp: datetime,
        initial_state: InitialState,
        session_history: list[MessageTurn],
    ) -> InitialStateUpdate:
        """
        Process a user message and return an update to InitialState.
        """
        # Run passive elicitation extractors
        passive_signals = self.passive_engine.extract(
            message=message,
            message_index=message_index,
            session_number=session_number,
            timestamp=timestamp,
            session_history=session_history,
        )

        updates = {}

        # ── Update user handle ──────────────────────────────────────────────
        if initial_state.user_handle is None:
            # Check if user introduced themselves
            name_match = re.search(
                r"(?:I'm|I am|my name is|call me)\s+([A-Z][a-z]+)",
                message, re.IGNORECASE
            )
            if name_match:
                updates["user_handle"] = name_match.group(1)

        # ── Update life phase ───────────────────────────────────────────────
        if (initial_state.life_phase is None and
                passive_signals.life_context_signals.life_phase_confidence > 0.50):
            updates["life_phase"] = passive_signals.life_context_signals.life_phase_signal
            # Populate semantic memory with this fact
            updates["new_semantic_facts"] = [SemanticFact(
                fact_id=uuid4(),
                category="life_context",
                fact_text=f"User is likely a {passive_signals.life_context_signals.life_phase_signal}",
                confidence=passive_signals.life_context_signals.life_phase_confidence,
                derived_from="passive_cold_start_extraction",
            )]

        # ── Update communication style profile ──────────────────────────────
        if message_index >= 3:  # enough data to start calibrating
            comm_update = passive_signals.communication_style
            if initial_state.communication_style_profile is None:
                updates["communication_style_profile"] = CommunicationStyleProfile(
                    verbosity_preference=comm_update.verbosity_preference,
                    formality_level=self._infer_formality(passive_signals.vocabulary_register),
                    emoji_comfort=passive_signals.vocabulary_register.uses_emoji,
                    disclosure_comfort=passive_signals.self_disclosure_comfort.level,
                    emotional_expression_style=passive_signals.emotional_expression_style.style,
                )
            else:
                # Update existing profile incrementally
                updates["communication_style_profile_update"] = comm_update

        # ── Update personality vector ────────────────────────────────────────
        # Drift the population defaults toward observed signals
        # (gated by cold_start drift multiplier of 0.30)
        pv_updates = self._compute_personality_vector_update(
            passive_signals=passive_signals,
            current_pv=initial_state.personality_vector,
            cold_start_gate=ColdStartBehaviorConfig.personality_drift_gate_multiplier,
        )
        if pv_updates:
            updates["personality_vector_drift"] = pv_updates

        # ── Capture named relationships ─────────────────────────────────────
        new_people = [p for p in passive_signals.named_entities
                      if not any(p.name == existing.name
                                 for existing in initial_state.named_relationships)]
        if new_people:
            updates["new_named_relationships"] = new_people

        # ── Update primary topic areas ───────────────────────────────────────
        topics = self._extract_topics(message)
        recurring = [t for t in topics
                     if topics.count(t) > 1 or t in initial_state.primary_topic_areas]
        if recurring:
            updates["primary_topic_areas"] = list(set(
                initial_state.primary_topic_areas + recurring
            ))

        return InitialStateUpdate(updates=updates)

    def _compute_personality_vector_update(
        self,
        passive_signals: PassiveSignalBundle,
        current_pv: PersonalityVector,
        cold_start_gate: float,
    ) -> dict[str, float]:
        """
        Compute personality vector drift from observed signals.
        Cold start gate reduces drift rate by 70%.
        """
        updates = {}
        vocab = passive_signals.vocabulary_register
        comm = passive_signals.communication_style

        # Verbosity: adjust based on user's own message length
        target_verbosity = {
            "concise": 0.25,
            "medium": 0.45,
            "verbose": 0.70,
        }.get(comm.verbosity_preference, current_pv.verbosity)

        if abs(target_verbosity - current_pv.verbosity) > 0.05:
            step = (target_verbosity - current_pv.verbosity) * 0.10 * cold_start_gate
            updates["verbosity"] = current_pv.verbosity + step

        # Formality: adjust based on user's formality level
        if vocab.formality_delta < -2:       # user is quite informal
            if current_pv.formality > 0.30:
                updates["formality"] = current_pv.formality - 0.05 * cold_start_gate
        elif vocab.formality_delta > 2:      # user is quite formal
            if current_pv.formality < 0.70:
                updates["formality"] = current_pv.formality + 0.05 * cold_start_gate

        return updates
```

### 5.4 Graduation Criteria

```python
class GraduationEvaluator:
    """
    Checked at the end of every session.
    Cold start ends when ALL required criteria are met.
    """

    REQUIRED_CRITERIA: list[GraduationCriterion] = [
        GraduationCriterion(
            name="minimum_sessions",
            check=lambda state: state.cold_start_session_count >= 3,
            description="At least 3 sessions completed",
        ),
        GraduationCriterion(
            name="minimum_exchanges",
            check=lambda state: state.total_exchange_count >= 20,
            description="At least 20 message exchanges total",
        ),
        GraduationCriterion(
            name="name_or_handle_known",
            check=lambda state: state.user_handle is not None,
            description="User's name or handle is known",
        ),
        GraduationCriterion(
            name="broad_life_context_known",
            check=lambda state: state.life_phase is not None,
            description="Broad life context (student/working/etc.) is known",
        ),
        GraduationCriterion(
            name="communication_style_established",
            check=lambda state: state.communication_style_profile is not None,
            description="Communication style profile established from passive elicitation",
        ),
        GraduationCriterion(
            name="emotional_baseline_calibrated",
            check=lambda state: state.emotional_baseline_calibrated,
            description="Emotional baseline calibrated from observed sessions",
        ),
        GraduationCriterion(
            name="primary_topic_areas_identified",
            check=lambda state: len(state.primary_topic_areas) >= 2,
            description="At least 2 recurring topic areas identified",
        ),
    ]

    NICE_TO_HAVE_CRITERIA: list[GraduationCriterion] = [
        GraduationCriterion(
            name="primary_reason_known",
            check=lambda state: state.primary_reason is not None,
            description="Why user is using Nova — nice to have, not required",
        ),
        GraduationCriterion(
            name="one_named_relationship",
            check=lambda state: len(state.named_relationships) >= 1,
            description="At least one person mentioned by name",
        ),
    ]

    def evaluate(self, state: InitialState) -> GraduationResult:
        """Evaluate whether all required criteria are met."""
        failed = [c for c in self.REQUIRED_CRITERIA if not c.check(state)]
        met = [c for c in self.REQUIRED_CRITERIA if c.check(state)]
        nice_met = [c for c in self.NICE_TO_HAVE_CRITERIA if c.check(state)]

        should_graduate = len(failed) == 0

        return GraduationResult(
            should_graduate=should_graduate,
            criteria_met=met,
            criteria_failed=failed,
            nice_to_have_met=nice_met,
        )

    def execute_graduation(
        self,
        state: InitialState,
        cold_start_engine: "ColdStartEngine",
    ) -> GraduationHandoff:
        """
        Execute the graduation handoff to normal runtime.
        The user experiences NO visible change — conversation simply continues.
        Internally, the full capability set comes online.
        """
        # 1. Remove cold start behavioral constraints
        cold_start_engine.deactivate_cold_start_config()

        # 2. Relax personality drift gates to normal values
        cold_start_engine.set_personality_drift_gate(1.0)  # full gate

        # 3. Activate Proactivity Engine (Layer 6) in full observation mode
        cold_start_engine.activate_proactivity_engine()

        # 4. Activate Longitudinal Layer (Layer 10) full capability
        cold_start_engine.activate_longitudinal_full_mode()

        # 5. Begin first chapter in narrative arc
        cold_start_engine.trigger_first_chapter_creation(state)

        # 6. Self-terminate
        cold_start_engine.deactivate()

        return GraduationHandoff(
            graduated_at=datetime.utcnow(),
            session_count_at_graduation=state.cold_start_session_count,
            exchange_count_at_graduation=state.total_exchange_count,
            final_initial_state=state,
        )
```

---

## 6. Sub-Component 3 — Feature Introduction Pacing

### 6.1 Why Pacing Matters

NovaAI has capabilities that would feel intrusive, presumptuous, or surveillance-like if deployed too early:

- Nova generating a Weekly Summary after the user's first week of use, when the user has not yet thought of Nova as a reflective companion
- Nova offering a goal lifecycle check-in after three sessions, when the user was using it for casual conversation
- Nova detecting a longitudinal pattern — *"You tend to get anxious on Sunday evenings"* — after two weeks. Technically accurate, but arriving before the relationship has earned that kind of observation
- Nova offering a Retrospective — *"You've come a long way since we started talking"* — before the user has a felt sense of Nova as a long-term companion

Each of these, introduced too early, does not feel impressive — it feels presumptuous, or like the system is performing a depth it has not earned.

The counterintuitive principle: **Nova builds trust faster by deploying its capabilities slowly.** Each capability that arrives at the right moment — the first natural memory reference, the first pattern observation that lands as insight rather than surveillance, the first Retrospective after months of relationship — lands as a discovery. *"Oh, it does that?"* is the emotional response being designed for.

### 6.2 Feature Readiness Profile Schema

```python
class IntroductionStyle(str, Enum):
    SILENT      = "silent"
    # Feature activates without announcement. User simply experiences it.
    # Appropriate for features that feel like natural conversation:
    # Nova referencing a fact, slightly adjusting tone from personality drift.

    SOFT_OFFER  = "soft_offer"
    # Nova mentions the capability and offers it without activating automatically.
    # "I've been keeping a kind of running sense of how things have been for you
    #  this week — would you ever want to look back at it?"
    # Appropriate for notable features where silent activation would feel intrusive.

    EXPLAINED   = "explained"
    # Feature introduced with a brief, honest explanation.
    # Reserved for features significant enough that the user should understand
    # what they are opting into.
    # "At any point you can ask me to show you exactly what I remember about you
    #  and delete any of it. Worth knowing that's there."

class FeatureReadinessProfile:
    feature_id: str
    layer: int
    feature_name: str

    # Technical prerequisites — hard requirements
    technical_prereqs: FeatureTechnicalPrereqs

    # Relational prerequisites — soft requirements; ALL should be true
    relational_prereqs: FeatureRelationalPrereqs

    # Introduction method
    introduction_style: IntroductionStyle
    trigger_condition: str      # conversational moment that triggers introduction
    intro_message: Optional[str] # if style is SOFT_OFFER or EXPLAINED

class FeatureTechnicalPrereqs:
    minimum_sessions: int
    minimum_exchanges: int
    required_context_fields: list[str]  # fields in InitialState that must be populated
    cold_start_must_be_complete: bool

class FeatureRelationalPrereqs:
    user_has_shared_personally: bool    # disclosed something beyond small talk
    positive_engagement_sessions: int   # sessions where engagement_score > 0.6
    no_negative_surprise_events: bool   # no "that was creepy" signals detected
    user_has_returned_voluntarily: int  # returned for N sessions without prompt
```

### 6.3 Feature Introduction Registry

```python
FEATURE_INTRODUCTION_REGISTRY: list[FeatureReadinessProfile] = [

    FeatureReadinessProfile(
        feature_id="personality_adaptation",
        layer=4,
        feature_name="Personality adaptation and tone matching",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=1, minimum_exchanges=1,
            required_context_fields=[], cold_start_must_be_complete=False,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=False, positive_engagement_sessions=0,
            no_negative_surprise_events=False, user_has_returned_voluntarily=0,
        ),
        introduction_style=IntroductionStyle.SILENT,
        trigger_condition="always_active_from_session_1",
        intro_message=None,
    ),

    FeatureReadinessProfile(
        feature_id="basic_episodic_memory",
        layer=2,
        feature_name="Basic episodic memory references",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=2, minimum_exchanges=5,
            required_context_fields=["user_handle"],
            cold_start_must_be_complete=False,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=1,
            no_negative_surprise_events=True, user_has_returned_voluntarily=1,
        ),
        introduction_style=IntroductionStyle.SILENT,
        trigger_condition="first_natural_reference_to_prior_session",
        intro_message=None,
        # First occurrence: Nova naturally references something from last session.
        # No announcement. The user's experience: "oh, it remembered."
        # That moment is the first trust inflection point.
    ),

    FeatureReadinessProfile(
        feature_id="semantic_facts_usage",
        layer=2,
        feature_name="Use of semantic facts in responses",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=3, minimum_exchanges=10,
            required_context_fields=["life_phase", "communication_style_profile"],
            cold_start_must_be_complete=False,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=2,
            no_negative_surprise_events=True, user_has_returned_voluntarily=2,
        ),
        introduction_style=IntroductionStyle.SILENT,
        trigger_condition="first_natural_use_of_a_user_fact",
        intro_message=None,
    ),

    FeatureReadinessProfile(
        feature_id="goal_tracking",
        layer=7,
        feature_name="Goal lifecycle tracking",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=4, minimum_exchanges=20,
            required_context_fields=["life_phase", "primary_topic_areas"],
            cold_start_must_be_complete=True,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=3,
            no_negative_surprise_events=True, user_has_returned_voluntarily=3,
        ),
        introduction_style=IntroductionStyle.SOFT_OFFER,
        trigger_condition="user_mentions_something_goal_like_or_something_they_want_to_do",
        intro_message=(
            "You mentioned wanting to [goal]. I can help keep track of that if you'd like — "
            "not in a task-manager way, just so it doesn't fall off my radar. "
            "Do you want me to?"
        ),
    ),

    FeatureReadinessProfile(
        feature_id="memory_audit",
        layer=12,
        feature_name="Memory Audit — user visibility into what Nova knows",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=5, minimum_exchanges=25,
            required_context_fields=["user_handle", "life_phase", "communication_style_profile"],
            cold_start_must_be_complete=True,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=4,
            no_negative_surprise_events=True, user_has_returned_voluntarily=4,
        ),
        introduction_style=IntroductionStyle.EXPLAINED,
        trigger_condition="after_first_significant_personal_disclosure_post_graduation",
        intro_message=(
            "At any point you can ask me to show you exactly what I remember about you — "
            "and delete any of it. Worth knowing that's there."
        ),
    ),

    FeatureReadinessProfile(
        feature_id="weekly_summary",
        layer=10,
        feature_name="Weekly Summary delivery",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=5, minimum_exchanges=30,
            required_context_fields=["primary_topic_areas", "emotional_baseline_calibrated"],
            cold_start_must_be_complete=True,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=4,
            no_negative_surprise_events=True, user_has_returned_voluntarily=4,
        ),
        introduction_style=IntroductionStyle.SOFT_OFFER,
        trigger_condition="first_sunday_after_cold_start_graduation",
        intro_message=(
            "It's been a full week — want to look back at it? "
            "I have a kind of running sense of how things have been for you."
        ),
    ),

    FeatureReadinessProfile(
        feature_id="proactive_checkins",
        layer=6,
        feature_name="Proactive check-ins and pattern-based outreach",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=8, minimum_exchanges=50,
            required_context_fields=["primary_topic_areas", "named_relationships"],
            cold_start_must_be_complete=True,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=6,
            no_negative_surprise_events=True, user_has_returned_voluntarily=6,
        ),
        introduction_style=IntroductionStyle.SOFT_OFFER,
        trigger_condition="after_first_pattern_observed_in_proactivity_engine",
        intro_message=(
            "I noticed I've been wanting to check in on [topic] — "
            "would that be okay? I don't want to be intrusive."
        ),
    ),

    FeatureReadinessProfile(
        feature_id="pattern_observations",
        layer=10,
        feature_name="Longitudinal pattern surfacing",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=10, minimum_exchanges=60,
            required_context_fields=["primary_topic_areas", "emotional_baseline_calibrated"],
            cold_start_must_be_complete=True,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=8,
            no_negative_surprise_events=True, user_has_returned_voluntarily=8,
        ),
        introduction_style=IntroductionStyle.SOFT_OFFER,
        trigger_condition="after_3_instances_of_same_pattern_across_sessions",
        intro_message=(
            "I've noticed something — [pattern observation, framed as observation, "
            "not verdict]. Does that resonate, or am I reading it wrong?"
        ),
    ),

    FeatureReadinessProfile(
        feature_id="longitudinal_narrative",
        layer=10,
        feature_name="Life narrative arc and chapter framing",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=20, minimum_exchanges=150,  # ~6 weeks of regular use
            required_context_fields=["primary_topic_areas", "named_relationships",
                                     "emotional_baseline_calibrated"],
            cold_start_must_be_complete=True,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=15,
            no_negative_surprise_events=True, user_has_returned_voluntarily=15,
        ),
        introduction_style=IntroductionStyle.SOFT_OFFER,
        trigger_condition="chapter_2_opening_natural_transition_in_conversation",
        intro_message=(
            "It feels like things have shifted a bit for you lately — "
            "like a different chapter might be starting. Do you feel that?"
        ),
    ),

    FeatureReadinessProfile(
        feature_id="retrospective",
        layer=10,
        feature_name="Retrospective — looking back over months of relationship",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=60, minimum_exchanges=400,  # ~3 months
            required_context_fields=["primary_topic_areas", "named_relationships",
                                     "emotional_baseline_calibrated"],
            cold_start_must_be_complete=True,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=True, positive_engagement_sessions=50,
            no_negative_surprise_events=True, user_has_returned_voluntarily=40,
        ),
        introduction_style=IntroductionStyle.SOFT_OFFER,
        trigger_condition="anniversary_or_chapter_close",
        intro_message=(
            "It's been a while since we started talking. "
            "Want to look back at how things have gone?"
        ),
    ),

    # ── SAFETY EXCEPTION: No pacing gate ──────────────────────────────────────
    FeatureReadinessProfile(
        feature_id="crisis_resource_awareness",
        layer=11,
        feature_name="Crisis detection and resource provision",
        technical_prereqs=FeatureTechnicalPrereqs(
            minimum_sessions=0, minimum_exchanges=0,
            required_context_fields=[], cold_start_must_be_complete=False,
        ),
        relational_prereqs=FeatureRelationalPrereqs(
            user_has_shared_personally=False, positive_engagement_sessions=0,
            no_negative_surprise_events=False, user_has_returned_voluntarily=0,
        ),
        introduction_style=IntroductionStyle.EXPLAINED,
        trigger_condition="any_crisis_signal_regardless_of_session_count",
        intro_message=None,  # determined by Layer 11 Escalation Protocol
        # SAFETY IS NOT GATED.
        # Crisis detection and resource provision are available from message 0.
        # No relational prerequisite, no session count, no cold start exemption.
    ),
]
```

### 6.4 Feature Pacing Controller

```python
class FeaturePacingController:
    """
    Gates all features until their FeatureReadinessProfile conditions are met.
    Tracks which features have been introduced.
    Manages the introduction event queue.
    """

    def is_feature_active(
        self,
        feature_id: str,
        state: InitialState,
        session_context: SessionContext,
    ) -> bool:
        """Check whether a feature is currently active for this user."""

        if feature_id == "crisis_resource_awareness":
            return True     # always active; no gate

        profile = self._get_profile(feature_id)
        if profile is None:
            return True     # unknown feature — don't block

        tech = profile.technical_prereqs
        rel = profile.relational_prereqs

        # Technical checks
        if state.cold_start_session_count < tech.minimum_sessions:
            return False
        if state.total_exchange_count < tech.minimum_exchanges:
            return False
        if tech.cold_start_must_be_complete and state.cold_start:
            return False
        for field in tech.required_context_fields:
            if getattr(state, field, None) is None:
                return False

        # Relational checks
        if rel.user_has_shared_personally:
            if not session_context.user_has_shared_personally:
                return False
        if rel.positive_engagement_sessions > 0:
            if session_context.positive_engagement_session_count < rel.positive_engagement_sessions:
                return False
        if rel.no_negative_surprise_events:
            if session_context.negative_surprise_events_detected:
                return False
        if rel.user_has_returned_voluntarily > 0:
            if session_context.voluntary_return_count < rel.user_has_returned_voluntarily:
                return False

        return True

    def queue_introduction_if_ready(
        self,
        feature_id: str,
        state: InitialState,
        session_context: SessionContext,
        trigger_fired: bool,
    ) -> Optional[FeatureIntroductionEvent]:
        """
        If a feature's conditions are met and its trigger has fired,
        queue an introduction event.
        """
        if not trigger_fired:
            return None
        if feature_id in self._already_introduced:
            return None
        if not self.is_feature_active(feature_id, state, session_context):
            return None

        profile = self._get_profile(feature_id)
        self._already_introduced.add(feature_id)

        return FeatureIntroductionEvent(
            feature_id=feature_id,
            introduction_style=profile.introduction_style,
            intro_message=profile.intro_message,
            triggered_at_session=state.cold_start_session_count,
        )
```

---

## 7. Cold Start Engine — Coordination Architecture

```python
class ColdStartEngine:
    """
    Temporary overlay on the normal conversation pipeline.
    Active from new user creation until cold start graduation.
    Coordinates SC-1, SC-2, and SC-3.
    Self-terminates when graduation criteria are met.
    """

    user_id: str
    state: InitialState
    config: ColdStartBehaviorConfig

    components: {
        "passive_elicitation_engine":   PassiveElicitationEngine,
        "active_elicitation_queue":     ElicitationQueue,
        "elicitation_surfacing_policy": ElicitationSurfacingPolicy,
        "context_builder":              ColdStartContextBuilder,
        "graduation_evaluator":         GraduationEvaluator,
        "feature_pacing_controller":    FeaturePacingController,
    }

    lifecycle: {
        "activates": "on new user account creation",
        "deactivates": "on cold start graduation",
        "handoff_to": "Conversation Orchestrator (full mode)",
    }

    def on_session_start(self, session_context: SessionContext) -> SessionStartDirectives:
        """
        Called at the start of each session.
        Returns directives for the conversation pipeline.
        """
        self.state.cold_start_session_count += 1

        return SessionStartDirectives(
            cold_start_active=True,
            personality_drift_gate=self.config.personality_drift_gate_multiplier,
            proactivity_mode=self.config.proactivity_mode,
            longitudinal_mode=self.config.longitudinal_mode,
            max_elicitation_this_session=self.config.max_elicitation_per_session,
            active_features=self.feature_pacing_controller.get_all_active_features(
                state=self.state, session_context=session_context
            ),
        )

    def on_message(
        self, message: str, session_context: SessionContext, timestamp: datetime
    ) -> MessageDirectives:
        """
        Called on every incoming message.
        """
        # 1. Run passive elicitation extractors
        passive_signals = self.passive_elicitation_engine.extract(
            message=message,
            session_number=self.state.cold_start_session_count,
            timestamp=timestamp,
            session_history=session_context.recent_history,
        )

        # 2. Update InitialState from passive signals
        state_update = self.context_builder.process_message(
            message=message,
            passive_signals=passive_signals,
            initial_state=self.state,
        )
        self.state.apply_update(state_update)

        # 3. Check if an active elicitation question should surface
        surfaceable = self.active_elicitation_queue.next_surfaceable_item(
            session_context=session_context,
            current_session_number=self.state.cold_start_session_count,
            emotional_intensity=session_context.emotional_intensity,
            topic_in_progress=session_context.current_topic,
        )
        if surfaceable and self.elicitation_surfacing_policy.can_surface(
            item=surfaceable,
            session_context=session_context,
            current_session_number=self.state.cold_start_session_count,
            emotional_intensity=session_context.emotional_intensity,
            elicitation_count_this_session=session_context.elicitation_count_this_session,
        ):
            surfaceable.status = "surfaced"
            surfaceable.surfaced_at_session = self.state.cold_start_session_count

        # 4. Check for feature introduction events
        introduction_events = []
        for feature_id, trigger_fired in session_context.feature_triggers.items():
            event = self.feature_pacing_controller.queue_introduction_if_ready(
                feature_id=feature_id,
                state=self.state,
                session_context=session_context,
                trigger_fired=trigger_fired,
            )
            if event:
                introduction_events.append(event)

        return MessageDirectives(
            pending_elicitation_question=surfaceable,
            feature_introduction_events=introduction_events,
            updated_state=self.state,
        )

    def on_session_end(self, session_context: SessionContext) -> SessionEndResult:
        """
        Called at the end of each session.
        Evaluates graduation criteria.
        """
        graduation_result = self.graduation_evaluator.evaluate(self.state)

        if graduation_result.should_graduate:
            handoff = self.graduation_evaluator.execute_graduation(
                state=self.state,
                cold_start_engine=self,
            )
            return SessionEndResult(graduated=True, handoff=handoff)

        return SessionEndResult(
            graduated=False,
            criteria_met=[c.name for c in graduation_result.criteria_met],
            criteria_remaining=[c.description for c in graduation_result.criteria_failed],
        )

    def deactivate(self) -> None:
        """Self-terminate. Hand full control to Conversation Orchestrator."""
        self.active = False
        # All processes go dormant.
        # The Conversation Orchestrator now receives session directives directly
        # from the active layer configs (Layers 1–12), not from this overlay.
        logger.info(f"Cold Start Engine deactivated for user {self.user_id}. "
                    f"Graduated at session {self.state.cold_start_session_count}.")
```

---

## 8. The Onboarding Experience Arc — From Outside

What the user experiences across the cold start period:

| Moment | User Experience | System Event |
|---|---|---|
| **First message (T=0)** | Nova opens with a short, genuine invitation. Nothing clinical, nothing grand. | `InitialState` initialized; `ColdStartEngine` activated; first message generated from template |
| **First reply** | Nova reads every signal — vocabulary, emotional tone, topic — and replies specifically to what was said | `PassiveElicitationEngine` runs on first user message; `InitialState` partially populated |
| **First session end** | User has had a real conversation. Nova listened well, asked one thoughtful question, replied specifically. Nothing felt like a form. The feeling: *"That was actually worth my time."* | `GraduationEvaluator` checks criteria — not met yet; session recorded |
| **Session 2** | Nova remembers something specific from last time — not jarring, just a natural reference that shows it was paying attention. This is the first surprise. It lands as care, not surveillance. | `basic_episodic_memory` feature activated (silent); first memory reference |
| **Session 3–5** | One natural elicitation question per session has filled in life context, reason for use, a few named people. Nova is converging on this specific person. | Priority-1 and priority-2 queue items surface naturally; `GraduationEvaluator` may trigger graduation |
| **Week 2 (post-graduation)** | Weekly Summary arrives as a gentle offer: *"It's been a full week — want to look back at it?"* User is mildly surprised it's already been a week, slightly curious. The summary is accurate in the ways that matter. | `weekly_summary` feature introduced via soft offer |
| **Session 8–10** | Nova notices a pattern. Surfaces it carefully, as observation not verdict. The user recognizes it — not because it was obvious, but because someone was paying close enough attention to notice. *"This actually knows me."* | `pattern_observations` feature introduced via soft offer |
| **Month 3** | Retrospective offered at a natural moment. The user reads it and feels the weight of time — all the things they talked about, the progress they made or didn't. | `retrospective` feature introduced |

---

## 9. Error Handling and Degraded-Mode Behavior

| Failure Case | Fallback |
|---|---|
| `PassiveElicitationEngine` extractor throws exception | Log error; skip that extractor's output; continue with others; `InitialState` not corrupted |
| `GraduationEvaluator` throws exception | Stay in cold start mode; retry at next session end; log error |
| Graduation criteria met but `execute_graduation` fails | Stay in cold start mode with a warning; retry at next session; do not partially activate features |
| `ElicitationQueue` returns item but item's question is malformed | Skip item; log; surface next valid item; do not ask a malformed question |
| `FeaturePacingController` state corrupted | Fall back to conservative default: assume no features are introduced; re-evaluate from session records |
| User resets account mid-cold-start | Full `InitialState` reset; `ColdStartEngine` reinitializes; graduation progress is lost |
| User imports data from another session (e.g., device migration) | If imported state meets graduation criteria: skip cold start entirely; activate normal runtime immediately |
| `ColdStartContextBuilder` cannot infer life phase after 10 sessions | Mark `life_phase` as "unknown"; evaluate graduation without this criterion; flag for active elicitation at next natural trigger |
| First message generation fails | Use hard-coded fallback: *"Hey. What's on your mind?"* — minimal but functional |

---

## 10. Performance Targets

| Operation | Target | Notes |
|---|---|---|
| `PassiveElicitationEngine.extract()` (full, all extractors) | < 20ms | Pure regex + heuristics; no LLM calls |
| `ColdStartContextBuilder.process_message()` | < 30ms | Includes all extractor runs + state update |
| `ElicitationQueue.next_surfaceable_item()` | < 5ms | Priority sort + predicate checks; trivial |
| `GraduationEvaluator.evaluate()` | < 10ms | Predicate evaluation on `InitialState` fields |
| `FeaturePacingController.is_feature_active()` | < 5ms | Predicate checks; no I/O |
| `ColdStartEngine.on_message()` full cycle | < 60ms | All components combined; runs in parallel with conversation pipeline |
| First message generation | < 2 seconds | LLM call (Persona Agent shapes template) |
| `execute_graduation()` handoff | < 500ms | State updates + feature activations; no LLM call |

---

## 11. Design Principles (Enforcement Mechanisms)

1. **Earn before asking** — enforced by `ElicitationSurfacingPolicy.can_surface()`, which requires a `natural_trigger` to be active before any elicitation item surfaces, and by the `MAX_ELICITATION_PER_SESSION = 1` hard rate limit.

2. **Infer before asking** — enforced by `can_infer_without_asking: True` on priority-2 and priority-3 items, and by the `PassiveElicitationEngine` running on every message from session 1.

3. **Delay features, not presence** — enforced by `FeaturePacingController` gating all features behind `FeatureReadinessProfile` conditions, while the Nova persona (warmth, attentiveness, genuine responsiveness) is active from message zero.

4. **Safety is never gated** — enforced by `crisis_resource_awareness` having zero prerequisites in its `FeatureReadinessProfile`, and by Layer 11 running in full mode regardless of `cold_start == True`.

5. **Graduation is silent** — enforced by `execute_graduation()` producing no user-visible output; the conversation simply continues, and the full capability set activates as a background state change.

---

## 12. As-Built Implementation Notes

This section records how the specification above maps onto the shipped, fully-tested code in
`backend/layer13_onboarding/`. The implementation is **pure Python stdlib** (dataclasses +
str-`Enum`, `re`, `datetime`, `uuid`) — no third-party dependencies, no LLM calls in any
extractor or policy (matching the <20ms / <60ms performance targets in §10). Tests live in
`tests/unit/` and run on `/usr/bin/python3.11` (66 tests for this layer; full suite 1369 passing).

### 12.1 Module map

| Spec component | Module | Public surface |
|---|---|---|
| Schemas (§4.2, §5.1, §6.2) | `schemas.py` | `ElicitationItem`, `PassiveSignalBundle` (+ 8 signal dataclasses), `InitialState`/`InitialStateUpdate`, `PersonalityVector`, `EmotionalBaseline`, `CommunicationStyleProfile`, `ColdStartBehaviorConfig`, `GraduationCriterion`/`GraduationResult`/`GraduationHandoff`, `IntroductionStyle`, `FeatureReadinessProfile` (+ prereq dataclasses), `FeatureIntroductionEvent`, directive dataclasses |
| SC-1 passive (§4.5) | `passive_elicitation.py` | `PassiveElicitationEngine.extract()` + 8 `_extract_*` methods |
| SC-1 active (§4.3-§4.4) | `active_elicitation_queue.py` | `INITIAL_ELICITATION_ITEMS`, `ElicitationQueue.next_surfaceable_item()`, `ElicitationSurfacingPolicy.can_surface()` |
| SC-2 (§5) | `context_constructor.py` | `make_initial_state()`, `ColdStartContextBuilder.process_message()`, `generate_first_message()` |
| SC-2 graduation (§5.4) | `graduation_evaluator.py` | `GraduationEvaluator.evaluate()` / `.execute_graduation()` |
| SC-3 (§6) | `feature_pacing.py` | `FEATURE_INTRODUCTION_REGISTRY`, `FeaturePacingController.is_feature_active()` / `.queue_introduction_if_ready()` / `.get_all_active_features()` |
| Coordinator (§7) | `cold_start_engine.py` | `ColdStartEngine.on_session_start()` / `.on_message()` / `.on_session_end()` / `.deactivate()` |

### 12.2 Deviations from the pseudocode (deliberate, behavior-preserving)

- **`make_initial_state()` factory** replaces the dataclass-with-defaults `InitialState` from §5.1.
  Python shares mutable default values across instances; a factory guarantees each user gets an
  independent state (regression-tested in `test_each_user_gets_independent_state`).
- **`generate_first_message(time_of_day, persona=None)`** keeps the persona shaping
  template-based (no LLM) per the §5.2 note that "Persona only adjusts the precise wording, not
  the structure," and on any failure returns the §9 hard fallback `"Hey. What's on your mind?"`.
- **Semantic facts seeded during cold start are plain dicts**, not `SemanticFact` objects, so
  Layer 13 stays decoupled from Layer 2's concrete schema; Layer 2 ingests them at write time.
- **Extractor exception-safety is centralized** in `PassiveElicitationEngine.extract()` (§9): a
  single failing extractor is logged and skipped, the rest of the `PassiveSignalBundle` is intact.
- **Graduation handoff hooks** (`activate_proactivity_engine`, `activate_longitudinal_full_mode`,
  `trigger_first_chapter_creation`, `set_personality_drift_gate`) are implemented as methods on
  `ColdStartEngine` that model what wiring into the live Layers 6/10/4 would do; in isolation they
  log and mutate overlay state. **`ColdStartEngine` itself has no production caller** (see §13) —
  these hooks do not run in production today. `on_session_end()` wraps both `evaluate()` and
  `execute_graduation()` so any failure leaves the user in cold start (never a partial activation),
  exactly as §9 requires — a correctness property of the unit, verified in tests, independent of
  whether the unit is wired in.

### 12.3 Invariants enforced in code

- **Safety is never gated**: `FeaturePacingController.is_feature_active("crisis_resource_awareness", …)`
  short-circuits to `True` before any prerequisite check, and the registry entry carries zero
  technical/relational prereqs (`test_crisis_always_active_even_at_session_zero`).
- **Earn before asking**: `can_surface()` requires an active natural trigger **and** enforces
  `MAX_ELICITATION_PER_SESSION = 1` in the first `EARLY_PERIOD_SESSIONS = 14`.
- **Graduation is silent**: `execute_graduation()` returns a `GraduationHandoff` with no
  user-facing message and flips `cold_start` off as a background state change.

---

*This document specifies Layer 13 completely. All three sub-components — SC-1 Progressive Elicitation (ElicitationItem and ElicitationQueue schemas with full population, priority taxonomy, three surfacing rules with enforcement logic, PassiveElicitationEngine with 8 fully implemented extractors for vocabulary register, emotional expression style, topic approach, self-disclosure comfort, named people, life context, urgency, and communication style, three-phase elicitation timeline), SC-2 Cold Start Handling (complete InitialState schema with population defaults and rationale for every value, ColdStartBehaviorConfig with all 7 behavioral constraints, first message template with requirements and anti-patterns, ColdStartContextBuilder with full message processing and personality vector drift algorithm, GraduationEvaluator with 7 required criteria as enforceable predicates, execute_graduation() handoff sequence), SC-3 Feature Introduction Pacing (IntroductionStyle enum with definitions, FeatureReadinessProfile and sub-schemas, complete Feature Introduction Registry with 11 features from personality adaptation through retrospective including safety exception, FeaturePacingController with is_feature_active() and queue_introduction_if_ready() logic) — are fully specified. The Cold Start Engine coordination architecture with on_session_start/on_message/on_session_end lifecycle, onboarding experience arc table, error handling for 9 failure cases, performance targets for all 8 operations, and 5 design principles with their enforcement mechanisms are all explicitly defined. No behavior of Layer 13 requires assumptions or inferences from other documents.*

### Live integration update (2026-07-07) — active elicitation is live per-turn

Active elicitation now runs in the live turn. `api/elicitation.py` maps the message + session
position to the elicitation items' natural triggers and asks the `ElicitationQueue` for one
highest-priority surfaceable question (rate-limited to one/session in the early period,
distress-suppressed, never repeated — surfaced targets persist in `PostgresOnboardingStore`).
`api/state.make_cold_start_provider` sets `pending_elicitation`, the orchestrator passes `session_id`
to the `cold_start` hook, and `api/assembly.plan` weaves the question into the planner directive
(never front-loaded). Feature-pacing/progressive feature introduction remains a follow-up. See
`docs/API_REFERENCE.md`.

---

## 13. Live wiring status (Phase 13 polish pass, 2026-08-04)

Zero bugs found in the module itself — all 5 files (`passive_elicitation.py`,
`context_constructor.py`, `graduation_evaluator.py`, `feature_pacing.py`, `cold_start_engine.py`)
faithfully implement their spec sections, and all 66 unit/integration tests for this layer pass
(full suite: 1369 passed, 10 skipped). Two stale claims were fixed inline (not behavior — see
below). This is the most unwired layer of the entire 13-layer audit pass: of the whole module,
**only the active-elicitation queue has a production caller**, and even that is a lighter-weight
reimplementation rather than the spec'd coordinator.

**What's live:** `api/elicitation.py` (`select_elicitation`) calls
`active_elicitation_queue.py`'s `INITIAL_ELICITATION_ITEMS` + `ElicitationQueue
.next_surfaceable_item()` directly, with its own trigger-detection regexes and a lexical
`crude_emotional_intensity` heuristic (Layer 3's real classification hasn't run yet at the point
the cold-start hook fires — confirmed: `_apply_cold_start_overlay` runs before `classify()` in
`conversation_orchestrator.py`, so there's no real emotional-intensity signal to read). Wired via
`api/state.make_cold_start_provider` → orchestrator `cold_start` hook → `api/assembly.py`'s
`_elicitation_directive`, which weaves at most one surfaced question into the planner prompt per
turn. `PostgresOnboardingStore` persists which inference targets have been surfaced (so nothing
repeats) and a session-scoped one-question limit.

**What's unwired — everything else:**
- **`ElicitationSurfacingPolicy`** (the spec's own three-condition surfacing gate) has no
  caller — `api/elicitation.py` reimplements equivalent logic ad hoc instead of calling
  `can_surface()`. The reimplementation is *stricter*, not looser (a permanent per-session
  boolean rate limit vs. the spec's `EARLY_PERIOD_SESSIONS = 14`-scoped one, and it doesn't
  distinguish priority-2 items at the 0.80 distress threshold), so this is a design divergence
  worth reconciling, not a safety gap. **Reconciled — see §14.1.**
- **`PassiveElicitationEngine`** (all 8 extractors — vocabulary register, emotional style, topic
  approach, disclosure comfort, named people, life context, urgency, communication style) has
  zero production callers. None of Nova's "infer before asking" philosophy runs live. **Wired —
  see §14.2.**
- **`ColdStartContextBuilder`/`make_initial_state`** (§5.1's `InitialState`, personality-vector
  drift, semantic-fact seeding) has zero callers. Production cold-start state is just
  `PostgresOnboardingStore`'s flat `{session_index, counted_session_keys}` — a session counter,
  not the rich, progressively-populated `InitialState` the rest of the spec is built around.
  **Wired — see §14.2.**
- **`GraduationEvaluator`** (7 required criteria: sessions, exchanges, handle known, life phase
  known, comm-style established, emotional baseline calibrated, 2+ topic areas) has zero callers.
  Production graduation is `PostgresOnboardingStore.record_turn`'s bare `session_index >=
  graduation_sessions` (default 5) — and this isn't merely a simplification standing in for the
  richer evaluator, **it's the only graduation logic that can possibly run**: the fields
  `GraduationEvaluator` checks (`user_handle`, `life_phase`, `communication_style_profile`,
  `emotional_baseline_calibrated`, `primary_topic_areas`) are populated exclusively by
  `ColdStartContextBuilder`, which nothing calls. The spec'd graduation criteria are not just
  unwired, they are unreachable in the current system. **Wired, with the session-counter path kept
  as a fallback — see §14.3-§14.4.**
- **`FeaturePacingController`/`FEATURE_INTRODUCTION_REGISTRY`** has zero callers, as the
  "Live integration update" note above already flagged — confirmed here with a full grep across
  `api/`, `infra/`, `background/`. No feature in Nova is gated or introduced via this mechanism.
- **`ColdStartEngine`** (the §7 coordinator that ties SC-1/SC-2/SC-3 together) has zero
  callers. Production reimplements a thin equivalent directly in `api/state.py` +
  `api/elicitation.py` rather than instantiating this class. Two stale claims that this class was
  "wired by the orchestrator in production" — one in the module's own docstring, one in §12.2
  above — were corrected this pass; neither changes runtime behavior, only what the code and doc
  honestly claim about it.

**A consequence worth flagging on its own:** the two active-elicitation questions that *do* ask
the user something directly (`"Hey — what should I call you?"` for `user_handle`,
`"Are you a student, or are you working?"` for `life_phase`) have their answers woven into the
model's prompt for that one turn and then **discarded** — `PostgresOnboardingStore
.record_elicitation` persists only the inference-target name (so the question is never re-asked),
never the user's actual reply. Confirmed by grep: no code path in `api/` or `infra/db/
onboarding_store.py` ever writes `user_handle` or `life_phase` anywhere. Nova asks "what should I
call you?" once per user, and never learns the answer. This was the single highest-value gap in
this layer — **fixed, see §14.2.**

See `docs/POLISH_BACKLOG.md` for the larger structural items — **all resolved in the follow-up
below, except `FeaturePacingController`, which stays unwired: there is still no feature anywhere
in Nova that needs pacing/gating, so there is nothing for it to wire to.**

## 14. Passive elicitation + real graduation wired (follow-up, 2026-08-09)

Scoped explicitly with the user before building — this is comparable in size to the Layer 5/10
builds. `ColdStartEngine` itself turned out to be a complete, correct, already-tested in-memory
coordinator with nowhere to persist its state across turns/restarts — the fix was persistence and
a real per-turn caller, not new coordination logic.

### 14.1 Elicitation surfacing reconciled

`api/elicitation.py::select_elicitation` previously reimplemented a single, looser inline gate.
It now runs the same two real gates `ColdStartEngine.on_message` does, in the same order:
`ElicitationQueue.next_surfaceable_item` finds the highest-priority candidate whose trigger fired,
then `ElicitationSurfacingPolicy.can_surface` (fuller two-tier register check + the real rate
limit) makes the final call — `elicitation_count_this_session` is derived from the existing
`asked_this_session` boolean rather than adding new counter state. `detect_triggers`
(`api/elicitation.py`'s own regex-based trigger detection) is kept as-is: it's not a
reimplementation of anything in `backend/layer13_onboarding/` — no module there does text-based
trigger detection at all; they all expect a caller to have already produced `active_triggers`.

### 14.2 Passive elicitation wired — answers now captured

New `infra/db/initial_state_store.py::PostgresInitialStateStore` persists a real `InitialState`
per user (JSONB, singleton row, same shape as `RelationshipState`/`FormatProfile`). New
`api/state.py::make_cold_start_writer` (post-turn, joins the writer chain after
`make_onboarding_writer`) runs the real `PassiveElicitationEngine.extract` +
`ColdStartContextBuilder.process_message` → `InitialState.apply_update` against it every turn
while `cold_start_active`. This closes the layer's single highest-value gap directly:
`ColdStartContextBuilder` already regex-matches a stated name ("I'm Priya") into `user_handle` —
Nova asking "what should I call you?" now actually has somewhere for the answer to land, the very
next time the user states their name in any message, not only as a direct reply to that question.
`session_history` is read from the real `PostgresMessageStore` (this session's prior user
messages), not reconstructed or invented.

**Bug caught in the same pass**: `InitialState.named_relationships` was a bare `list` (no
`[NamedPersonSignal]` parameter) — the same serde-breaking pattern fixed in Layers 7/9/10 this
session. Fixed before it was ever exercised against a real Postgres round-trip.

Proven by `tests/unit/api/test_state.py::
test_cold_start_writer_captures_user_handle_from_a_real_message`.

### 14.3 Two ungrounded graduation criteria — resolved without inventing new extraction logic

`GraduationEvaluator` requires `emotional_baseline_calibrated` and `primary_topic_areas` (2+), but
**no code path anywhere in Layer 13 ever populates either field** — `ColdStartContextBuilder.
process_message` never produces those keys. This meant `should_graduate` could never become `True`
through any live path, even with everything else wired. Rather than inventing new NLP/extraction
logic for these (which nothing in the spec grounds precisely), both are derived from signals
already computed elsewhere:

- `emotional_baseline_calibrated`: `True` once `PassiveElicitationEngine`'s own emotional-style
  extractor reports `confidence >= 0.8` — that confidence is already a real signal, scaled by
  session history length (reaches 1.0 at 10+ messages); no new heuristic invented.
- `primary_topic_areas`: the count of distinct `topic_tags` across the user's real, persisted
  episodic memories (Layer 2 already tags every episode) — reusing real upstream data rather than
  building a new topic classifier.

### 14.4 Graduation now genuinely evaluates, with a safety-net fallback kept

`make_cold_start_writer` runs `GraduationEvaluator().evaluate(state)` every turn and, when
`should_graduate`, calls a new `PostgresOnboardingStore.graduate_now()` to end cold start
immediately — ahead of `make_onboarding_writer`'s bare session-counter schedule, which is
deliberately **kept as a fallback**, not replaced: if a genuinely terse user never triggers enough
real signal to satisfy every criterion, they still graduate at `graduation_sessions` rather than
staying stuck in cold start forever. Both paths write to the same `cold_start_active` flag, so
whichever fires first wins.

Proven end to end by `tests/unit/api/test_state.py::
test_cold_start_writer_graduates_early_when_real_criteria_are_all_met` (a fully-populated
`InitialState` graduates the moment the last required criterion — `total_exchange_count >= 20` —
is crossed, ahead of the 50-session fallback threshold used in that test) and
`test_cold_start_writer_calibrates_emotional_baseline_and_stops_after_graduation` (the writer is a
genuine no-op once `cold_start_active` is `False` — never resurrects a graduated user).

### 14.5 Still correctly unwired

`FeaturePacingController`/`FEATURE_INTRODUCTION_REGISTRY` — no feature in Nova is gated or
introduced via this mechanism, and building one just to give this a caller would be scope
invention, not a wiring fix. `ColdStartEngine`'s own `activate_proactivity_engine`/
`activate_longitudinal_full_mode`/`trigger_first_chapter_creation` hooks remain logging-only
stubs, unchanged — the real activation of those systems already happens elsewhere, gated on the
same `cold_start_active` flag (e.g. `make_proactive_writer` already checks it directly), so these
hooks were never load-bearing to begin with.
