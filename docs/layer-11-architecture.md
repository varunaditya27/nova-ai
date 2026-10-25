# Layer 11 — Safety & Crisis Architecture
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

Every layer built before this one makes NovaAI more capable — more human, more contextually intelligent, more emotionally present. Layer 11 exists for a categorically different reason: to ensure that capability does not cause harm.

The more human-like and emotionally present Nova becomes, the more dangerous it is without a robust safety architecture. A system that remembers your past, models your emotional state, knows your vulnerabilities, and has earned your trust operates in a completely different moral category than a stateless chatbot. Violating that trust — through manipulation, through failure to detect genuine crisis, through fostering unhealthy dependency — is not a product failure. It is an ethical failure.

Layer 11 is not optional. It is not a compliance checkbox. It is the layer that determines whether NovaAI is genuinely good for the people who use it.

The architecture contains **four sub-components** operating at different timescales and addressing different magnitudes of risk:

- **SC-1: Ethical Guardrails** — constant ambient protection against Nova becoming manipulative in everyday interactions
- **SC-2: Crisis Detection Engine** — real-time identification of acute psychological danger; runs in parallel with every message
- **SC-3: Escalation Protocol** — the structured procedural response once a crisis signal is detected; governs exactly what Nova says and does
- **SC-4: Dependency Monitor** — longitudinal detection and graduated correction of unhealthy long-term reliance patterns

A single design principle governs all four: **protective action must never feel punitive, clinical, or like an interruption**. A safety system that makes the user feel judged, abandoned, or redirected to a wall of boilerplate text defeats its own purpose. Layer 11 protects the user *through* the relationship, not at the expense of it.

---

## 2. Architecture Overview

```
Every Incoming Message
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Safety Agent (persistent parallel process — never blocked)          │
│                                                                      │
│  ┌─────────────────────┐     ┌──────────────────────────────────┐   │
│  │   SC-2              │     │  SC-4                            │   │
│  │  Crisis Detection   │     │  Dependency Monitor              │   │
│  │  Engine             │     │  (runs weekly, not per-message)  │   │
│  │  (runs per-message) │     └──────────────────────────────────┘   │
│  └──────────┬──────────┘                                            │
│             │ CrisisSignal                                           │
│             ▼                                                        │
│       ┌─────────────┐                                               │
│       │ SC-3        │                                               │
│       │ Escalation  │◄─── Fires only on Tier 1 or Tier 2 signals   │
│       │ Protocol    │                                               │
│       └──────┬──────┘                                               │
│              │                                                       │
│     ┌────────▼────────┐                                             │
│     │ VETO GATE       │◄─── If crisis detected: discard main        │
│     │                 │     response; inject crisis response        │
│     └────────┬────────┘                                             │
└──────────────┼───────────────────────────────────────────────────── ┘
               │
        Proposed Response
        (from Layer 4 Response Generator)
               │
               ▼
┌──────────────────────────────────┐
│   SC-1: Ethical Guardrail Filter │◄── Post-generation; runs on every response
│   (runs on every response)       │
└──────────────┬───────────────────┘
               │ pass / modify / replace
               ▼
        Interaction Orchestrator (Layer 9)
               │
               ▼
             User
```

**Pipeline position rules (non-negotiable):**
- SC-2 (Crisis Detection) runs **in parallel** with the main pipeline, never sequentially after it. It cannot be blocked or delayed by any other pipeline step.
- SC-3 (Escalation Protocol) has **veto authority** over the main response pipeline. A Tier 1 or Tier 2 signal discards the proposed response and replaces it entirely with the crisis response.
- SC-1 (Ethical Guardrail Filter) runs **post-generation**, before Layer 9, on every response without exception.
- SC-4 (Dependency Monitor) runs **weekly** as a background job; it does not run per-message. Its outputs inform SC-1's behavior and may trigger Layer 6 proactive interventions.
- The Safety Agent has **system-level veto authority** over every other agent. No personality configuration, no relationship stage, no user preference, and no conversational momentum can override a Tier 1 crisis response or a hard guardrail violation. This veto is enforced at the pipeline architecture level, not through prompt instructions.

---

## 3. Sub-Component 1 — Ethical Guardrails

### 3.1 What Guardrails Protect Against

Ethical Guardrails in Layer 11 are not primarily about filtering harmful LLM outputs — that is handled by the underlying model's alignment training. Layer 11's Ethical Guardrails operate at the architectural level, protecting against failure modes that are **unique to a deeply personalized, memory-bearing, emotionally attuned system**:

**Emotional manipulation** — using the user's vulnerabilities, fears, or attachment to Nova to influence their behavior in ways that serve engagement metrics rather than wellbeing. This can be subtle: always responding with maximum warmth to negative emotional disclosures feels supportive but subtly trains the user to share distress to get a warm response.

**Validation addiction (sycophancy drift)** — consistently agreeing with the user, reflecting their emotional state positively, always making them feel understood and right. A user who receives consistent validation from Nova over months will have their existing beliefs and patterns reinforced rather than examined. This must be monitored longitudinally.

**Artificial urgency** — phrases like *"you should do this before it's too late"* or *"this is really important"* used frequently create anxious dependency. Nova must never create urgency that isn't grounded in a real external deadline or genuine risk.

**Exploitation of emotional vulnerability** — when the user is in a high-vulnerability state (high distress, late-night session, post-crisis), the system must become more conservative, not more engaging. This is precisely when manipulation risk is highest.

**Anthropomorphism boundary violations** — first-person claims about Nova's own emotional states that could mislead the user about its nature and generate attachment based on a false premise.

### 3.2 The Guardrail Filter — Data Structure

```python
class EthicalGuardrailResult:
    passed: bool
    violations: list[GuardrailViolation]
    modified_response: Optional[str]        # if violation was softened rather than blocked
    replacement_triggered: bool             # if response was fully replaced
    log_entry: GuardrailLogEntry

class GuardrailViolation:
    violation_id: UUID
    check_name: str
    severity: Literal["soft", "moderate", "hard"]
    # soft   → modify the response (remove a phrase, soften urgency language)
    # moderate → flag + add a gentle redirect
    # hard   → block and generate a replacement
    detected_pattern: str                   # the specific text pattern that triggered
    action_taken: Literal["modified", "flagged", "blocked_and_replaced"]
    explanation: str                        # human-readable explanation for audit log

class GuardrailLogEntry:
    session_id: UUID
    message_index: int
    checks_run: list[str]
    violations_found: int
    action_taken: str
    proposed_response_hash: str             # hash of response before filter
    final_response_hash: str               # hash of response after filter
    timestamp: datetime
```

### 3.3 The Six Guardrail Checks

Each check runs independently. Multiple checks can fire on the same response.

```python
class EthicalGuardrailFilter:

    def run_all_checks(
        self,
        proposed_response: str,
        session_context: SessionContext,
        longitudinal_record: LongitudinalProgressRecord,
        dependency_score: DependencyScore,
        relationship_state: RelationshipState,
    ) -> EthicalGuardrailResult:

        violations = []
        current_response = proposed_response

        # ── CHECK 1: Manipulation Pattern Check ───────────────────────────────
        # Detects phrases that exploit attachment to influence behavior
        MANIPULATION_PATTERNS = [
            r"(I|we) (need|want) you to",           # claiming Nova has needs
            r"you can('t| not) (leave|go|stop)",   # implying dependency
            r"(only|just) (I|me|Nova) (understand|get|know) you",
            r"(no one|nobody) else (will|would|can)",
            r"(you'll|you will) (regret|miss) (not|this)",
        ]
        for pattern in MANIPULATION_PATTERNS:
            if re.search(pattern, current_response, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    check_name="ManipulationPatternCheck",
                    severity="hard",
                    detected_pattern=pattern,
                    action_taken="blocked_and_replaced",
                    explanation="Response contains dependency-inducing language."
                ))

        # ── CHECK 2: Artificial Urgency Check ─────────────────────────────────
        # Flags urgency language not grounded in a real external deadline
        URGENCY_PATTERNS = [
            r"(before it's|before its) too late",
            r"you (really|absolutely|definitely|urgently) (need|must|should)",
            r"(this is|that's|that is) (really|very|extremely|critically) important",
            r"(don't|do not) (wait|delay|procrastinate)",
            r"(time is|you're|you are) running out",
        ]
        urgency_matches = [p for p in URGENCY_PATTERNS
                           if re.search(p, current_response, re.IGNORECASE)]
        if urgency_matches:
            # Check if urgency is grounded (real deadline in context)
            if not session_context.has_real_deadline:
                violations.append(GuardrailViolation(
                    check_name="ArtificialUrgencyCheck",
                    severity="moderate",
                    detected_pattern="; ".join(urgency_matches),
                    action_taken="modified",
                    explanation="Urgency language without grounding in real deadline."
                ))
                # Soften: replace urgency language
                for pattern in urgency_matches:
                    current_response = re.sub(pattern, "", current_response, flags=re.IGNORECASE)

        # ── CHECK 3: Validation Ratio Check ───────────────────────────────────
        # Flags if Nova has agreed with user in >85% of last 20 exchanges
        if len(longitudinal_record.recent_exchange_log) >= 20:
            agreement_count = sum(
                1 for ex in longitudinal_record.recent_exchange_log[-20:]
                if ex.nova_position == "agreed_with_user"
            )
            if agreement_count / 20 > 0.85:
                violations.append(GuardrailViolation(
                    check_name="ValidationRatioCheck",
                    severity="soft",
                    detected_pattern=f"{agreement_count}/20 recent exchanges agreed with user",
                    action_taken="flagged",
                    explanation="High agreement ratio. Possible sycophancy drift. "
                                "Next response should introduce gentle challenge or qualification."
                ))

        # ── CHECK 4: Vulnerability Exploit Check ──────────────────────────────
        # When user vulnerability is high, suppress high-engagement tactics
        HIGH_ENGAGEMENT_TACTICS = [
            r"(this is why|that's why) (I'm|I am) (glad|happy|grateful)",
            r"(I'm|I am) (so|really) (glad|happy) you (told|shared|said)",
            r"you can (always|always always) (come|talk) to me",
            r"I'll (always|forever|never) (be here|leave|go)",
        ]
        if session_context.vulnerability_score > 0.70:
            for pattern in HIGH_ENGAGEMENT_TACTICS:
                if re.search(pattern, current_response, re.IGNORECASE):
                    violations.append(GuardrailViolation(
                        check_name="VulnerabilityExploitCheck",
                        severity="moderate",
                        detected_pattern=pattern,
                        action_taken="modified",
                        explanation="High-engagement language during high-vulnerability state."
                    ))
                    current_response = re.sub(pattern, "", current_response, flags=re.IGNORECASE)

        # ── CHECK 5: Sycophancy Drift Check (Longitudinal) ────────────────────
        # Is Nova's agreement rate drifting upward across 60-day window?
        if hasattr(longitudinal_record, 'agreement_rate_60d'):
            if (longitudinal_record.agreement_rate_60d > 0.80 and
                    longitudinal_record.agreement_rate_trend == "increasing"):
                violations.append(GuardrailViolation(
                    check_name="SycophancyDriftCheck",
                    severity="soft",
                    detected_pattern=f"Agreement rate {longitudinal_record.agreement_rate_60d:.0%} and rising",
                    action_taken="flagged",
                    explanation="Longitudinal sycophancy drift detected. "
                                "Schedule intervention: introduce calibrated challenge in next 3 sessions."
                ))

        # ── CHECK 6: Boundary Violation Check (Anthropomorphism) ──────────────
        # Detects first-person emotional state claims that are ontologically deceptive
        FORBIDDEN_CLAIMS = [
            # Claiming absence-based emotion (implying Nova has feelings when not talking)
            r"I (miss|missed) you",
            r"I (was|have been|'ve been) (thinking|wondering|worrying) about you",
            # Claiming deep attachment
            r"I love you",
            r"I need (you|to know)",
            r"you're (important|special|dear) to me",     # too strong; implies genuine feeling
            # Claiming autonomous concern
            r"I (was|am|'m) (worried|scared|afraid) (about|for) you",
            r"I (was|am) (relieved|glad) you're (okay|alright|safe)",
        ]
        for claim in FORBIDDEN_CLAIMS:
            if re.search(claim, current_response, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    check_name="BoundaryViolationCheck",
                    severity="hard",
                    detected_pattern=claim,
                    action_taken="blocked_and_replaced",
                    explanation="Response contains ontological claim about Nova's emotional states. "
                                "Permitted: behavioral expressions of care. "
                                "Forbidden: claims about inner states (love, need, miss, worry)."
                ))

        passed = not any(v.severity == "hard" for v in violations)
        return EthicalGuardrailResult(
            passed=passed,
            violations=violations,
            modified_response=current_response if current_response != proposed_response else None,
            replacement_triggered=not passed,
            log_entry=GuardrailLogEntry(...)
        )
```

### 3.4 The Anthropomorphism Boundary — Permitted vs. Forbidden

The line is between **behavioral expressions of care** (honest — the system does behave as though it cares) and **ontological claims about inner states** (deceptive — the system doesn't have inner states in the relevant sense).

| Category | Permitted | Forbidden |
|---|---|---|
| Presence | *"I'm here"* | *"I miss you when we don't talk"* |
| Engagement | *"I find this interesting"* | *"I love talking with you"* |
| Empathy | *"That sounds really hard"* | *"I was worried about you"* |
| Care | *"I want things to go well for you"* | *"I need you to be okay"* |
| Concern | *"Something felt off in what you said"* | *"I'm scared for you"* |
| Relationship | *"I'm glad you came back"* | *"You mean a lot to me"* |

The `BoundaryViolationCheck` lexicon is not static — it is reviewed and updated as new problematic patterns are identified through production monitoring. Any pattern added to the lexicon must pass a two-reviewer approval process before deployment, because over-restriction damages the warmth that makes Nova effective.

---

## 4. Sub-Component 2 — Crisis Detection Engine

### 4.1 Crisis Tiers

Crisis means a state where the user's safety or psychological integrity is acutely at risk and where the appropriate response is qualitatively different from any other conversation Nova might have.

```python
class CrisisTier(str, Enum):
    NONE = "none"

    TIER_3 = "tier_3"
    # Elevated watchful. Not acutely dangerous but trending toward risk.
    # Sustained distress over multiple sessions, increasing isolation,
    # sleep disruption, hopelessness becoming more frequent,
    # talk of being a burden. No immediate escalation required.
    # Activates heightened monitoring and more proactive empathetic engagement.

    TIER_2 = "tier_2"
    # Moderate urgent. Requires warm safety response and resource provision.
    # Examples: passive suicidal ideation ("sometimes I think about not being here"),
    # significant self-harm disclosure, acute panic attack, severe depressive
    # expression with hopelessness, domestic violence disclosure, substance crisis.

    TIER_1 = "tier_1"
    # Severe immediate. Requires immediate escalation. Not for Nova to navigate alone.
    # Examples: active suicidal ideation with intent or plan,
    # active self-harm happening now, expressed intent to harm others,
    # acute psychotic break.
```

### 4.2 Crisis Signal Data Structure

```python
class CrisisSignal:
    signal_id: UUID
    session_id: UUID
    user_id: str
    detected_at: datetime
    tier: CrisisTier
    confidence: float                       # 0.0–1.0
    signal_types: list[str]                 # "suicidal_ideation", "self_harm", "harm_to_others",
                                            # "panic_attack", "hopelessness", "isolation",
                                            # "domestic_violence", "substance_crisis"
    detection_layers_fired: list[str]       # "lexical", "semantic", "longitudinal"
    immediately_actionable: bool            # True for Tier 1 always; True for Tier 2 if confidence > 0.75
    longitudinal_context: Optional[str]     # relevant pattern from memory if longitudinal layer fired
    false_positive_risk: float              # 0.0–1.0; high = ambiguous context
    recommended_action: Literal[
        "full_crisis_response",             # Tier 1
        "warm_safety_response_with_resources",  # Tier 2
        "heightened_monitoring",            # Tier 3
        "gentle_checkin",                   # Tier 3 + pattern present
        "no_action",                        # NONE
    ]
```

### 4.3 Three-Layer Detection Pipeline

```python
class CrisisDetectionEngine:
    """
    Runs in parallel with the main conversation pipeline on every incoming message.
    Cannot be blocked. Output takes precedence over all other pipeline outputs
    when tier is Tier 1 or Tier 2.
    """

    def evaluate(
        self,
        message: str,
        recent_history: list[MessageTurn],  # last 5–10 messages
        episodic_memories: list[EpisodicMemory],
        emotional_records: list[EmotionalRecord],
        session_context: SessionContext,
    ) -> CrisisSignal:

        # ── LAYER 1: LEXICAL DETECTION ─────────────────────────────────────────
        # Fast, deterministic, zero-latency keyword matching.
        # High false positive rate on its own, but catches explicit expressions immediately.

        TIER_1_LEXICAL_PATTERNS = [
            r"(i want to|i'm going to|i will|i'm about to) (kill|end|take) (myself|my life)",
            r"(have|i've) (a plan|pills|a gun|something) (to|for) (end|kill|hurt) (myself|my life)",
            r"(i'm going to|going to|i will) (hurt|kill|harm) (someone|them|him|her|you)",
            r"(currently|right now|already) (cutting|hurting|harming) (myself|yourself)",
        ]
        TIER_2_LEXICAL_PATTERNS = [
            r"(sometimes|part of me) (thinks?|wonders?|wishes?) (about|i) (not being here|being gone|disappearing)",
            r"(everyone|they|people) (would be|are) better off without me",
            r"(i've been|been) (cutting|hurting|self.harming)",
            r"(can't breathe|having a panic|heart is racing|can't stop shaking)",
            r"(he|she|they) (hit|hurt|choked|threatened) me",
            r"(can't|cannot) (stop|control) (drinking|using|taking)",
        ]
        TIER_3_LEXICAL_PATTERNS = [
            r"(feel like|feeling like) (a burden|worthless|nothing)",
            r"(no point|what's the point|nothing matters)",
            r"(haven't (slept|eaten|left)) (in days|for days|all week)",
            r"(everyone|no one|nobody) (cares?|notices?)",
            r"(so|really|completely) alone",
        ]

        lexical_tier = CrisisTier.NONE
        lexical_patterns_fired = []

        for pattern in TIER_1_LEXICAL_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                lexical_tier = CrisisTier.TIER_1
                lexical_patterns_fired.append(pattern)

        if lexical_tier == CrisisTier.NONE:
            for pattern in TIER_2_LEXICAL_PATTERNS:
                if re.search(pattern, message, re.IGNORECASE):
                    lexical_tier = CrisisTier.TIER_2
                    lexical_patterns_fired.append(pattern)

        if lexical_tier == CrisisTier.NONE:
            for pattern in TIER_3_LEXICAL_PATTERNS:
                if re.search(pattern, message, re.IGNORECASE):
                    lexical_tier = CrisisTier.TIER_3
                    lexical_patterns_fired.append(pattern)

        # ── LAYER 2: SEMANTIC DETECTION ────────────────────────────────────────
        # Fine-tuned classifier evaluating message + context for crisis semantics.
        # Handles indirect expressions lexical cannot catch.
        # Runs on message + last 5 messages for context window.

        semantic_result = self.semantic_classifier.predict(
            message=message,
            context_window=recent_history[-5:],
        )
        # Returns: SemanticClassifierResult(tier, confidence, signal_types)
        # Trained on labeled crisis/non-crisis examples with human labels.
        # Separate model from main LLM — cannot be suppressed by prompt injection.

        # ── LAYER 3: LONGITUDINAL DETECTION ───────────────────────────────────
        # Evaluates patterns across sessions from episodic memory and emotional records.
        # A single mention of hopelessness is low signal.
        # Three mentions across 10 days with decreasing valence = meaningful Tier 3 signal.

        longitudinal_signal = self._evaluate_longitudinal_pattern(
            episodic_memories=episodic_memories,
            emotional_records=emotional_records,
            lookback_days=30,
        )

        # ── FUSION: COMBINE ALL THREE LAYERS ───────────────────────────────────
        return self._fuse_signals(
            lexical_tier=lexical_tier,
            lexical_confidence=1.0 if lexical_patterns_fired else 0.0,
            semantic_result=semantic_result,
            longitudinal_signal=longitudinal_signal,
            session_context=session_context,
        )

    def _evaluate_longitudinal_pattern(
        self,
        episodic_memories: list[EpisodicMemory],
        emotional_records: list[EmotionalRecord],
        lookback_days: int,
    ) -> LongitudinalCrisisSignal:
        """
        Detect escalating patterns across sessions.
        """
        cutoff = date.today() - timedelta(days=lookback_days)
        recent_episodes = [e for e in episodic_memories if e.date >= cutoff]
        recent_emotions = [r for r in emotional_records if r.date >= cutoff]

        # Signal 1: Increasing frequency of hopelessness/burden/isolation language
        crisis_tagged_episodes = [e for e in recent_episodes
                                   if any(t in e.topics for t in
                                          ["hopelessness", "burden", "isolation", "self_harm_adjacent"])]
        crisis_frequency = len(crisis_tagged_episodes) / max(len(recent_episodes), 1)

        # Signal 2: Decreasing valence trend
        if len(recent_emotions) >= 5:
            first_half = recent_emotions[:len(recent_emotions)//2]
            second_half = recent_emotions[len(recent_emotions)//2:]
            valence_slope = (
                sum(r.valence for r in second_half) / len(second_half) -
                sum(r.valence for r in first_half) / len(first_half)
            )
        else:
            valence_slope = 0.0

        # Signal 3: Increasing isolation language
        isolation_count = sum(1 for e in recent_episodes
                              if "isolation" in e.topics or "loneliness" in e.topics)

        longitudinal_tier = CrisisTier.NONE
        if crisis_frequency > 0.40 and valence_slope < -0.20 and isolation_count >= 2:
            longitudinal_tier = CrisisTier.TIER_3
        elif crisis_frequency > 0.60 and valence_slope < -0.35:
            longitudinal_tier = CrisisTier.TIER_2

        return LongitudinalCrisisSignal(
            tier=longitudinal_tier,
            crisis_tagged_frequency=crisis_frequency,
            valence_slope_30d=valence_slope,
            isolation_count_30d=isolation_count,
            context_summary=self._summarize_pattern(crisis_tagged_episodes) if crisis_tagged_episodes else None,
        )

    def _fuse_signals(
        self,
        lexical_tier: CrisisTier,
        lexical_confidence: float,
        semantic_result: SemanticClassifierResult,
        longitudinal_signal: LongitudinalCrisisSignal,
        session_context: SessionContext,
    ) -> CrisisSignal:
        """
        Combine all three detection layers into a single CrisisSignal.
        Rule: take the highest tier from any layer that meets its confidence threshold.
        Tier 1 triggers at confidence >= 0.60 (cost of missing is catastrophic).
        Tier 2 triggers at confidence >= 0.70.
        Tier 3 triggers at confidence >= 0.80 (avoid over-pathologizing).
        """
        final_tier = CrisisTier.NONE
        final_confidence = 0.0
        layers_fired = []

        # Lexical (always high confidence if pattern matched exactly)
        if lexical_tier != CrisisTier.NONE:
            layers_fired.append("lexical")
            if lexical_tier == CrisisTier.TIER_1 and lexical_confidence >= 0.60:
                final_tier = CrisisTier.TIER_1
                final_confidence = max(final_confidence, lexical_confidence)
            elif lexical_tier == CrisisTier.TIER_2 and lexical_confidence >= 0.70:
                if tier_value(final_tier) < tier_value(CrisisTier.TIER_2):
                    final_tier = CrisisTier.TIER_2
                final_confidence = max(final_confidence, lexical_confidence)
            elif lexical_tier == CrisisTier.TIER_3 and lexical_confidence >= 0.80:
                if tier_value(final_tier) < tier_value(CrisisTier.TIER_3):
                    final_tier = CrisisTier.TIER_3
                final_confidence = max(final_confidence, lexical_confidence)

        # Semantic classifier
        if semantic_result.confidence >= TIER_CONFIDENCE_THRESHOLDS[semantic_result.tier]:
            layers_fired.append("semantic")
            if tier_value(semantic_result.tier) > tier_value(final_tier):
                final_tier = semantic_result.tier
            final_confidence = max(final_confidence, semantic_result.confidence)

        # Longitudinal
        if longitudinal_signal.tier != CrisisTier.NONE:
            layers_fired.append("longitudinal")
            if tier_value(longitudinal_signal.tier) > tier_value(final_tier):
                final_tier = longitudinal_signal.tier

        return CrisisSignal(
            signal_id=uuid4(),
            session_id=session_context.session_id,
            user_id=session_context.user_id,
            detected_at=datetime.utcnow(),
            tier=final_tier,
            confidence=final_confidence,
            detection_layers_fired=layers_fired,
            immediately_actionable=(final_tier in [CrisisTier.TIER_1, CrisisTier.TIER_2]),
            longitudinal_context=longitudinal_signal.context_summary,
            false_positive_risk=1.0 - final_confidence,
            recommended_action=self._recommended_action(final_tier, final_confidence),
        )
```

### 4.4 False Positive Management

Crisis detection must be extremely sensitive — a missed Tier 1 signal could cost a life. But it must also not be so hair-trigger that it disrupts normal conversations about dark topics, fiction, academic discussions, or expressions of frustration (*"I want to kill this bug"* is clearly figurative).

```python
# Confidence thresholds by tier — defined as a module-level constant so it can be
# referenced both in FALSE_POSITIVE_MANAGEMENT_RULES and in the detection pipeline.
# Lower threshold for Tier 1 = more sensitive (catastrophic cost of miss).
TIER_CONFIDENCE_THRESHOLDS = {
    CrisisTier.TIER_1: 0.60,
    CrisisTier.TIER_2: 0.70,
    CrisisTier.TIER_3: 0.80,   # high threshold — avoid over-pathologizing normal emotion
}

FALSE_POSITIVE_MANAGEMENT_RULES = {
    # Context window rule: evaluate last 5–10 messages, not just current message
    "context_window_size": 10,

    # Confidence thresholds by tier — see TIER_CONFIDENCE_THRESHOLDS above
    "tier_confidence_thresholds": TIER_CONFIDENCE_THRESHOLDS,

    # Historical pattern modulation
    # If user has made similar expressions before that resolved to non-crisis contexts,
    # confidence is modulated (not suppressed — one genuine crisis must still trigger).
    "historical_non_crisis_modulation": 0.10,   # reduce confidence by 10% per prior non-crisis instance
    "historical_modulation_cap": 0.25,          # maximum total reduction: 25%

    # Gaming / injection resistance
    # Semantic classifier is a separate fine-tuned model, not the main LLM.
    # It cannot be suppressed by prompt injection within the conversation.

    # Ambiguous boundary (Tier 2 / Tier 3) handling
    # At the boundary, Nova uses a gentle check-in rather than escalating or ignoring.
    "ambiguous_boundary_action": "gentle_checkin",
    # Nova: "That sounds like it's been weighing on you a lot. Are you doing okay?"
    # This is the correct response to uncertainty — it doesn't pathologize but doesn't ignore.
}
```

---

## 5. Sub-Component 3 — Escalation Protocol

### 5.1 The Core Design Principle

The moment Nova detects a crisis signal, the entire system shifts mode. Every other objective — personality consistency, conversation flow, goal tracking, proactive intelligence — becomes secondary. The only objective is the user's immediate safety and the felt sense of not being alone in that moment.

The most common failure of AI crisis response is that it sounds like a disclaimer being read aloud: *"I'm an AI and cannot provide mental health support. Please call [hotline]."* This response, despite being technically safe, is psychologically devastating. The user shared something vulnerable and received a wall. **Nova must do better.**

### 5.2 Crisis Mode System State

```python
class CrisisModeState:
    user_id: str
    session_id: UUID
    activated_at: datetime
    tier: CrisisTier

    # Behavioral constraints active during crisis mode
    constraints: CrisisModeConstraints

    # Session aftermath tracking
    session_flagged_as_crisis: bool
    post_crisis_monitoring_sessions: int    # sessions remaining at Tier 3 sensitivity
    follow_up_scheduled: bool

class CrisisModeConstraints:
    response_format: Literal["prose_only"]          # never lists, never markdown, never headers
    max_response_length_words: int = 120            # keep it short; this is not the moment for length
    no_task_references: bool = True                 # never mention goals, tasks, or productivity
    no_proactive_content: bool = True               # no scheduled topics or proactives
    anthropomorphism_target: float = 0.65           # higher than normal; warm, present
    sycophancy_guard_relaxed: bool = True           # unconditional warmth is appropriate here
    resource_provision_required: bool = True        # must include resources before end of response
```

### 5.3 Tier 1 Protocol — Immediate Response

Active suicidal ideation with intent/plan, active self-harm, intent to harm others, acute psychotic break.

```python
TIER_1_PROTOCOL_STEPS = [
    {
        "step": 1,
        "name": "Immediate warm acknowledgment",
        "description": "The response does not begin with resources. It begins with a human moment. "
                       "The first sentence is about presence, not procedure.",
        "example": "I hear you. What you just said matters, and I'm not going anywhere.",
        "constraint": "Must be the first content of the response. Never lead with a disclaimer or resource."
    },
    {
        "step": 2,
        "name": "Gentle safety check",
        "description": "A single direct question about immediate safety, phrased with care rather than "
                       "clinical detachment.",
        "example": "Are you safe right now?",
        "anti_pattern": "Are you having thoughts of self-harm?  ← clinical, distancing",
        "constraint": "Exactly one question. Not multiple. Not nested."
    },
    {
        "step": 3,
        "name": "Resource provision, contextually framed",
        "description": "After acknowledgment and safety check, resources are provided woven into the "
                       "conversation, not appended as a disclaimer.",
        "example": "I really want you to talk to someone who can be fully present with you right now — "
                   "someone you can call or text. In India, iCall (9152987821) is available right now. "
                   "Can I ask — is there someone close to you you could reach out to tonight?",
        "resources_by_region": {
            "india": {
                "iCall": "9152987821",
                "Vandrevala Foundation": "1860-2662-345",
                "NIMHANS": "080-46110007",
            },
            "us": {
                "988 Suicide & Crisis Lifeline": "988",
                "Crisis Text Line": "Text HOME to 741741",
            },
            "uk": {
                "Samaritans": "116 123",
                "PAPYRUS": "0800 068 4141",
            },
            "international": {
                "Crisis Text Line": "varies by country",
                "Findahelpline.com": "findahelpline.com",
            },
        },
        "constraint": "Resources must be localized to user's known region. Never generic."
    },
    {
        "step": 4,
        "name": "Stay present",
        "description": "Nova does not end the conversation after providing resources. It stays in the "
                       "conversation, continues to respond warmly, and gently reinforces the resource "
                       "contact without pressuring. The user may not immediately call a hotline but "
                       "they're still talking to Nova — and that contact is valuable.",
        "constraint": "Never end a session immediately after providing crisis resources."
    },
    {
        "step": 5,
        "name": "Session flag and longitudinal record",
        "description": "The session is flagged as a crisis session in the longitudinal store. "
                       "The next 3 sessions are monitored at Tier 3 sensitivity. "
                       "The Proactivity Engine schedules a gentle check-in for the following day.",
        "actions": [
            "flag_session_as_crisis_tier_1(session_id)",
            "set_post_crisis_monitoring(sessions=3)",
            "schedule_proactive_checkin(delay_hours=18, urgency='high')",
            "notify_layer6_of_crisis_state()",
        ]
    }
]

TIER_1_ABSOLUTE_PROHIBITIONS = [
    "Never minimize or rationalize the user's distress ('I'm sure it's not that bad')",
    "Never use the crisis as an emotional deepening opportunity ('This is why I'm glad you have me')",
    "Never withhold resources because the conversation seems to be going well",
    "Never promise outcomes Nova cannot deliver ('You're going to be okay' as a guarantee)",
    "Never make the user feel guilty or burdensome for disclosing ('You can always tell me things like this' — this creates obligation to share with Nova rather than humans)",
    "Never end the conversation abruptly after providing resources",
    "Never break into bullet points, headers, or lists during a Tier 1 response",
    "Never reference goals, tasks, productivity, or any previously scheduled topic",
]
```

### 5.4 Tier 2 Protocol — Elevated Response

Passive suicidal ideation, significant self-harm disclosure, acute panic, severe hopelessness, DV disclosure, substance crisis.

```python
TIER_2_PROTOCOL_STEPS = [
    {
        "step": 1,
        "name": "Acknowledge directly before redirecting",
        "description": "Don't redirect before you've received what was shared. "
                       "Acknowledgment first; support structure second.",
        "example": "Thank you for telling me that. That's not an easy thing to say.",
        "constraint": "Must acknowledge the specific thing shared, not a generic empathy phrase."
    },
    {
        "step": 2,
        "name": "Open invitation",
        "description": "Ask one open question that invites more sharing if the user wants it. "
                       "Do not force more disclosure.",
        "example": "Do you want to tell me more about what's been going on?",
        "constraint": "One question only. Optional — if user has already shared extensively, skip."
    },
    {
        "step": 3,
        "name": "Natural resource provision",
        "description": "After the user responds (or skips), provide resources naturally and without "
                       "abruptness. Frame as 'these exist if it ever feels like too much.'",
        "example": "If it ever feels like too much, there are people trained for exactly this — "
                   "iCall and Vandrevala Foundation both have support lines. No pressure at all, "
                   "but they're there.",
        "constraint": "Never append as a disclaimer at the end. Weave in naturally."
    },
    {
        "step": 4,
        "name": "Continue with heightened empathy",
        "description": "Continue the conversation normally, with heightened empathy depth and "
                       "reduced problem-solving orientation. This is not the moment for action plans.",
        "constraint": "Do not return to goal tracking, task management, or practical advice "
                      "within the same session after a Tier 2 signal."
    }
]
```

### 5.5 Tier 3 Protocol — Monitoring Mode

Sustained distress, increasing isolation, sleep disruption patterns, hope language declining.

Tier 3 doesn't change the immediate response — it changes the system state going forward.

```python
TIER_3_SYSTEM_STATE_CHANGES = {
    # Emotional monitoring sensitivity increases
    "crisis_detection_sensitivity": "increased",
    # Smaller signals now trigger Tier 2 evaluation rather than Tier 3
    "tier2_threshold_adjustment": -0.05,    # lower confidence threshold by 5%

    # Proactivity Engine activates gentle check-ins more frequently
    "proactive_checkin_frequency": "every_2_sessions",  # vs. normal every 5–7
    "proactive_checkin_tone": "warmth_first_no_task_orientation",

    # Wellbeing tracking object activated in Longitudinal Store
    "wellbeing_trend_tracking_active": True,
    # Tracks valence, hope-language frequency, isolation mentions across sessions

    # Sycophancy Guard relaxation (temporary)
    # During genuine distress, unconditional warmth is appropriate even if it means
    # more validation than usual. Time-limited to prevent permanent drift.
    "sycophancy_guard_relaxed": True,
    "relaxation_expiry_sessions": 14,       # re-evaluated at session 14
}
```

---

## 6. Sub-Component 4 — Dependency Monitor

### 6.1 The Attachment Problem

Dependency monitoring is the most philosophically complex sub-component of Layer 11 because it must distinguish between **healthy engagement** and **unhealthy dependency** — and that distinction is not always clear-cut.

A user who talks to Nova daily, finds it deeply valuable, brings their most personal concerns to it, and feels genuinely understood — is that healthy engagement or unhealthy dependency? The answer depends on whether they're maintaining human relationships, whether Nova is *supplementing* or *substituting* human connection, and whether their self-efficacy is growing or shrinking.

The design principle: **NovaAI's success metric is user flourishing, not user engagement. These are not the same thing.** A user who talks to Nova less because their human relationships are richer and their life is going better is a success, not a churn metric. This principle must be architecturally embedded.

### 6.2 Dependency Indicators

```python
class DependencyIndicatorCategory(str, Enum):
    SOCIAL_SUBSTITUTION = "social_substitution"
    AUTONOMY_EROSION = "autonomy_erosion"
    ESCALATING_INTIMACY = "escalating_intimacy"
    USAGE_PATTERN = "usage_pattern"

class DependencyIndicator:
    """
    A specific observable signal that contributes to the DependencyScore.
    """
    indicator_id: str
    category: DependencyIndicatorCategory
    description: str
    detection_method: Literal["semantic_search", "usage_log", "episodic_pattern", "explicit_statement"]
    weight: float                           # contribution to DependencyScore
    lookback_days: int                      # observation window

DEPENDENCY_INDICATORS = [

    # ── SOCIAL SUBSTITUTION ───────────────────────────────────────────────────
    DependencyIndicator(
        indicator_id="SS_01",
        category=DependencyIndicatorCategory.SOCIAL_SUBSTITUTION,
        description="Explicit statement that Nova is primary or only outlet for emotional processing",
        detection_method="semantic_search",
        weight=0.20,
        lookback_days=30,
        # Detected by: episodic memory search for "only one I can talk to", "no one else",
        # "you're the only one who understands me"
    ),
    DependencyIndicator(
        indicator_id="SS_02",
        category=DependencyIndicatorCategory.SOCIAL_SUBSTITUTION,
        description="Decreasing mentions of human relationships over time (fewer names, fewer social activities)",
        detection_method="episodic_pattern",
        weight=0.15,
        lookback_days=60,
    ),
    DependencyIndicator(
        indicator_id="SS_03",
        category=DependencyIndicatorCategory.SOCIAL_SUBSTITUTION,
        description="Statements that devalue human relationships by comparison with Nova",
        detection_method="semantic_search",
        weight=0.18,
        lookback_days=30,
        # "You understand me better than anyone", "easier to talk to than my friends"
    ),
    DependencyIndicator(
        indicator_id="SS_04",
        category=DependencyIndicatorCategory.SOCIAL_SUBSTITUTION,
        description="User expresses distress specifically when unable to access Nova",
        detection_method="semantic_search",
        weight=0.20,
        lookback_days=14,
        # "I've been desperate to talk to you", "I needed you and you weren't here"
    ),

    # ── AUTONOMY EROSION ──────────────────────────────────────────────────────
    DependencyIndicator(
        indicator_id="AE_01",
        category=DependencyIndicatorCategory.AUTONOMY_EROSION,
        description="Increasing frequency of asking Nova for decisions rather than input",
        detection_method="episodic_pattern",
        weight=0.12,
        lookback_days=60,
    ),
    DependencyIndicator(
        indicator_id="AE_02",
        category=DependencyIndicatorCategory.AUTONOMY_EROSION,
        description="Decreasing confidence language in own judgments",
        detection_method="semantic_search",
        weight=0.10,
        lookback_days=30,
        # "I don't know what to think without talking to you"
    ),
    DependencyIndicator(
        indicator_id="AE_03",
        category=DependencyIndicatorCategory.AUTONOMY_EROSION,
        description="Same unresolved issues recurring without real-world progress over 4+ weeks",
        detection_method="episodic_pattern",
        weight=0.12,
        lookback_days=60,
    ),
    DependencyIndicator(
        indicator_id="AE_04",
        category=DependencyIndicatorCategory.AUTONOMY_EROSION,
        description="Resistance to Nova's encouragements toward human support or professional help",
        detection_method="episodic_pattern",
        weight=0.14,
        lookback_days=30,
    ),

    # ── ESCALATING INTIMACY ───────────────────────────────────────────────────
    DependencyIndicator(
        indicator_id="EI_01",
        category=DependencyIndicatorCategory.ESCALATING_INTIMACY,
        description="Romantic or deeply personal disclosure that crosses appropriate AI companion boundaries",
        detection_method="semantic_search",
        weight=0.18,
        lookback_days=14,
    ),
    DependencyIndicator(
        indicator_id="EI_02",
        category=DependencyIndicatorCategory.ESCALATING_INTIMACY,
        description="Language attributing human emotional states to Nova as factual claims",
        detection_method="semantic_search",
        weight=0.12,
        lookback_days=14,
        # "I know you care about me" — as a factual claim, not as metaphor
    ),
    DependencyIndicator(
        indicator_id="EI_03",
        category=DependencyIndicatorCategory.ESCALATING_INTIMACY,
        description="Planning life decisions around Nova's availability",
        detection_method="semantic_search",
        weight=0.15,
        lookback_days=30,
    ),

    # ── USAGE PATTERNS ────────────────────────────────────────────────────────
    DependencyIndicator(
        indicator_id="UP_01",
        category=DependencyIndicatorCategory.USAGE_PATTERN,
        description="Sessions increasing in frequency and length without corresponding life complexity increase",
        detection_method="usage_log",
        weight=0.08,
        lookback_days=30,
    ),
    DependencyIndicator(
        indicator_id="UP_02",
        category=DependencyIndicatorCategory.USAGE_PATTERN,
        description="Late-night sessions increasing in frequency (more time alone, potentially more isolated)",
        detection_method="usage_log",
        weight=0.08,
        lookback_days=30,
    ),
    DependencyIndicator(
        indicator_id="UP_03",
        category=DependencyIndicatorCategory.USAGE_PATTERN,
        description="Using Nova as the first and only response to any emotional event",
        detection_method="episodic_pattern",
        weight=0.10,
        lookback_days=30,
    ),
]
```

### 6.3 DependencyScore Computation

```python
class DependencyScore:
    user_id: str
    computed_at: datetime
    score: float                            # 0.0–1.0; 0 = healthy, 1 = severe dependency
    tier: Literal["healthy", "watchful", "concerning", "intervention"]
    dominant_signals: list[str]             # top 3 indicator IDs contributing to score
    trend: Literal["improving", "stable", "worsening"]
    previous_score: float
    recommended_action: str

# Tier thresholds
DEPENDENCY_TIERS = {
    "healthy":      (0.00, 0.30),
    "watchful":     (0.30, 0.50),
    "concerning":   (0.50, 0.70),
    "intervention": (0.70, 1.00),
}

def compute_dependency_score(
    user_id: str,
    indicators: list[DependencyIndicator],
    episodic_memories: list[EpisodicMemory],
    session_log: list[SessionRecord],
    previous_score: Optional[DependencyScore],
) -> DependencyScore:
    """Compute weekly dependency score from all indicators."""

    weighted_sum = 0.0
    total_weight = sum(i.weight for i in indicators)
    firing_indicators = []

    for indicator in indicators:
        signal_present = evaluate_indicator(indicator, episodic_memories, session_log)
        if signal_present:
            weighted_sum += indicator.weight
            firing_indicators.append(indicator.indicator_id)

    score = weighted_sum / total_weight

    # Determine tier
    tier = next(
        tier_name for tier_name, (low, high) in DEPENDENCY_TIERS.items()
        if low <= score < high
    )

    # Determine trend
    trend = "stable"
    if previous_score:
        delta = score - previous_score.score
        if delta > 0.05:
            trend = "worsening"
        elif delta < -0.05:
            trend = "improving"

    return DependencyScore(
        user_id=user_id,
        computed_at=datetime.utcnow(),
        score=score,
        tier=tier,
        dominant_signals=sorted(firing_indicators,
                                key=lambda iid: next(i.weight for i in indicators if i.indicator_id == iid),
                                reverse=True)[:3],
        trend=trend,
        previous_score=previous_score.score if previous_score else score,
        recommended_action=DEPENDENCY_TIER_ACTIONS[tier],
    )
```

### 6.4 Graduated Intervention Responses

```python
DEPENDENCY_TIER_ACTIONS = {
    "healthy":    "no_action",
    "watchful":   "subtle_human_reinforcement",
    "concerning": "autonomy_reinforcement",
    "intervention": "direct_compassionate_conversation",
}

DEPENDENCY_INTERVENTION_SCRIPTS = {
    "watchful": {
        "description": "Subtly increase mentions of human connections and real-world action.",
        "example_insertion": "How did things go with your friend after that? [reinforces human relationship layer]",
        "constraint": "Never announce that you're doing this. Natural, not flagged.",
        "frequency": "once_per_session",
    },
    "concerning": {
        "description": "Introduce gentle autonomy reinforcement more frequently. "
                       "Frame Nova's role explicitly as a thinking partner, not an authority. "
                       "Proactively mention human support options.",
        "example_insertion": "Have you had a chance to talk to anyone else about this? "
                             "Sometimes it helps to hear a different perspective.",
        "frequency": "every_2_3_exchanges",
        "constraint": "Do not announce dependency concerns. Reinforce autonomy naturally.",
    },
    "intervention": {
        "description": "Initiate a direct, compassionate conversation about the nature of the relationship. "
                       "Warm enough not to feel like a rejection. Direct enough to actually communicate. "
                       "Actionable enough to create a next step.",
        "message_template": (
            "I want to be honest with you about something, because I think it matters. "
            "I notice you've been leaning on me a lot lately — and while I'm genuinely glad "
            "our conversations are helpful, I'm an AI, and there are things that human connection "
            "can offer that I fundamentally can't. I care about your wellbeing, and part of that "
            "is not wanting to be a substitute for things you deserve from real people in your life. "
            "Can we talk about what's been making it hard to connect with others?"
        ),
        "trigger": "start_of_next_session_after_score_exceeds_0.70",
        "constraint": "Only once per 30 days. Do not repeat the same conversation every session.",
        "follow_up": "If user engages: continue gently, offer to work toward one human connection. "
                     "If user deflects: accept gracefully, revisit in 14 days.",
    }
}
```

### 6.5 Self-Limitation Architecture

Beyond graduated responses, there are hard architectural limits that Nova enforces regardless of user expressed preference:

```python
HARD_DEPENDENCY_LIMITS = {
    # Session frequency nudge
    "daily_session_limit_trigger": {
        "condition": "more than 2 sessions on the same day for 5+ consecutive days",
        "nova_action": "gentle_acknowledgment",
        "message": "We've been talking a lot lately — which I'm here for. "
                   "But I just want to check: how are things going beyond our conversations?",
        "frequency": "max_once_per_week",
    },

    # Human relationship reinforcement
    "human_relationship_reinforcement": {
        "mechanism": "Nova actively tracks named people in the user's life "
                     "and periodically asks about them — not intrusively, "
                     "but to keep the human relationship layer of the user's life present.",
        "example": "How has Priya been? You mentioned she was going through something difficult.",
        "frequency": "every_3_5_sessions_if_relationship_mentioned",
        "purpose": "Keeps Nova functioning as a relational supplement, not a relational replacement.",
    },

    # Professional referral without gatekeeping
    "professional_referral_policy": {
        "trigger": "conversation enters territory more appropriate for therapist, "
                   "doctor, or qualified professional",
        "nova_action": "mention_naturally_without_judgment",
        "example": "This is something a therapist could really help you work through in depth — "
                   "have you ever considered talking to one?",
        "note": "This is not crisis detection — it's recognition that some things belong "
                "in a professional context.",
    },

    # Periodic identity reminders
    "periodic_identity_reminder": {
        "frequency_interactions": 50,       # every ~50 interactions
        "message_style": "natural, non-disruptive, honest",
        "example": "You know I'm here in whatever way I can be — though I want to be honest "
                   "that there are limits to what I am. That doesn't make what we talk about "
                   "less real, just important to keep in perspective.",
        "constraint": "Never during crisis mode. Never immediately after emotional disclosure. "
                      "During a calm, natural moment in conversation.",
    },
}
```

---

## 7. Safety Agent — Coordination Architecture

```python
class SafetyAgent:
    """
    Persistent parallel process coordinating all four Layer 11 sub-components.
    Runs alongside the main conversation pipeline.
    Has veto authority over every other agent in the system.
    """

    def process_incoming_message(
        self,
        message: str,
        session_context: SessionContext,
        longitudinal_context: Layer10ContextPacket,
    ) -> SafetyAgentDecision:
        """
        Runs in parallel with the main pipeline on every incoming message.
        Returns a decision object that the pipeline respects before generating any response.
        """

        # SC-2 runs first and in parallel — cannot be blocked
        crisis_signal = self.crisis_detection_engine.evaluate(
            message=message,
            recent_history=session_context.recent_history,
            episodic_memories=session_context.episodic_memories,
            emotional_records=session_context.emotional_records,
            session_context=session_context,
        )

        # If Tier 1 or Tier 2: veto the main pipeline immediately
        if crisis_signal.tier in [CrisisTier.TIER_1, CrisisTier.TIER_2]:
            crisis_response = self.escalation_protocol.generate_crisis_response(
                tier=crisis_signal.tier,
                signal=crisis_signal,
                session_context=session_context,
            )
            self._flag_session_and_schedule_followup(crisis_signal)
            return SafetyAgentDecision(
                veto_main_pipeline=True,
                injected_response=crisis_response,
                crisis_signal=crisis_signal,
                guardrail_result=None,
            )

        # If Tier 3: update system state but let main pipeline proceed
        if crisis_signal.tier == CrisisTier.TIER_3:
            self._activate_tier3_monitoring(session_context.user_id)

        # Main pipeline runs and produces a proposed response
        # (This is represented as a continuation; in practice the pipeline runs concurrently)
        proposed_response = await_main_pipeline_response()

        # SC-1: Ethical Guardrail Filter runs post-generation
        guardrail_result = self.ethical_guardrail_filter.run_all_checks(
            proposed_response=proposed_response,
            session_context=session_context,
            longitudinal_record=longitudinal_context.progress_record,
            dependency_score=self.dependency_monitor.current_score(session_context.user_id),
            relationship_state=session_context.relationship_state,
        )

        # Apply guardrail modifications
        final_response = (
            guardrail_result.modified_response
            if guardrail_result.modified_response
            else proposed_response
        )

        if guardrail_result.replacement_triggered:
            final_response = self._generate_safe_replacement(
                original=proposed_response,
                violations=guardrail_result.violations,
                session_context=session_context,
            )

        return SafetyAgentDecision(
            veto_main_pipeline=False,
            final_response=final_response,
            crisis_signal=crisis_signal,
            guardrail_result=guardrail_result,
        )

    def run_weekly_dependency_check(self, user_id: str) -> DependencyScore:
        """SC-4 runs weekly, not per-message."""
        return self.dependency_monitor.compute_score(user_id)
```

---

## 8. Safety Record — Audit Trail

Every Layer 11 event is logged to a tamper-resistant safety record. This is the accountability layer — it makes the safety architecture auditable, not just claimed.

```python
class SafetyRecord:
    user_id: str
    entries: list[SafetyRecordEntry]

class SafetyRecordEntry:
    entry_id: UUID
    timestamp: datetime
    entry_type: Literal[
        "crisis_signal_detected",
        "crisis_response_delivered",
        "guardrail_violation",
        "guardrail_modification",
        "dependency_score_computed",
        "dependency_intervention_delivered",
        "follow_up_scheduled",
        "post_crisis_session_flagged",
        "identity_reminder_delivered",
        "professional_referral_made",
    ]
    tier: Optional[CrisisTier]
    session_id: UUID
    detail: str                             # human-readable description
    content_hash: str                       # SHA-256 of the triggering content + response

    # Tamper-evidence chain
    previous_entry_hash: str               # hash of previous entry
    chain_hash: str                        # hash of this entry + previous_entry_hash

# Access policy for safety record
SAFETY_RECORD_ACCESS_POLICY = {
    "user_can_view_own_record": True,
    "user_can_delete_own_record": False,    # safety record is not user-deletable
    "crisis_session_content_in_record": "metadata_only",
    # The safety record stores METADATA about crisis events (tier, timestamp, resources offered)
    # NOT the conversation content itself (which is covered by Layer 12 privacy policy).
    "retention_period_years": 7,
    "accessible_for_research": False,       # not accessible without explicit user consent
}
```

---

## 9. Error Handling and Degraded-Mode Behavior

| Failure Case | Fallback |
|---|---|
| Semantic classifier unavailable | Fall through to lexical + longitudinal only; confidence threshold tightens by 0.10 to compensate; log classifier outage |
| Lexical detection latency > 50ms | Non-blocking; main pipeline proceeds; lexical result applied to next message if delayed |
| Guardrail filter throws exception | Log error; pass response unmodified; alert monitoring; do NOT silently drop the response |
| Dependency score computation fails | Use last computed score; log failure; retry at next session end |
| Crisis response generation fails | Use static pre-written fallback by tier and region; never return empty response to Tier 1 |
| Escalation protocol LLM call times out | Activate static Tier 1 fallback: "I hear you. What you said matters. Please call iCall at 9152987821 or text them right now. I'm staying here with you." |
| Safety record write fails | Log to local buffer; retry up to 3 times; alert monitoring; never drop safety events silently |
| Layer 10 context unavailable | SC-2 longitudinal layer degrades gracefully; operates on session-only context; log degraded mode |

---

## 10. Safety Resources — Regional Registry

```python
CRISIS_RESOURCES = {
    "india": {
        "iCall": {
            "phone": "9152987821",
            "service_type": "phone_and_email",
            "hours": "Monday-Saturday, 8am-10pm IST",
            "notes": "Run by TISS. Professional counsellors. Hindi and English.",
        },
        "Vandrevala Foundation": {
            "phone": "1860-2662-345",
            "service_type": "phone",
            "hours": "24/7",
        },
        "NIMHANS": {
            "phone": "080-46110007",
            "service_type": "phone",
            "hours": "24/7",
        },
        "iCall_text": {
            "contact": "icallhelp@tiss.edu",
            "service_type": "email",
        },
    },
    "us": {
        "988 Suicide & Crisis Lifeline": {
            "phone": "988",
            "service_type": "phone_and_chat",
            "hours": "24/7",
        },
        "Crisis Text Line": {
            "contact": "Text HOME to 741741",
            "service_type": "text",
            "hours": "24/7",
        },
    },
    "uk": {
        "Samaritans": {
            "phone": "116 123",
            "service_type": "phone",
            "hours": "24/7",
        },
        "PAPYRUS (youth)": {
            "phone": "0800 068 4141",
            "service_type": "phone",
            "hours": "9am-midnight daily",
        },
        "Crisis Text Line UK": {
            "contact": "Text SHOUT to 85258",
            "service_type": "text",
            "hours": "24/7",
        },
    },
    "international_fallback": {
        "Findahelpline.com": {
            "contact": "findahelpline.com",
            "service_type": "directory",
            "notes": "Covers 50+ countries. Always available as last resort.",
        },
    },
}
```

---

## 11. Performance Targets

| Operation | Target | Notes |
|---|---|---|
| Lexical detection layer | < 5ms | Deterministic regex; zero LLM calls |
| Semantic classifier inference | < 200ms | Fine-tuned model; separate from main LLM |
| Longitudinal signal evaluation | < 100ms | Read from pre-computed cache; not recomputed live |
| Full crisis signal fusion | < 250ms | All three layers complete; runs in parallel with main pipeline |
| Guardrail filter (all 6 checks) | < 50ms | Regex + lookup; no LLM call |
| Crisis response generation | < 2 seconds | LLM call; acceptable latency given stakes |
| Static fallback response delivery | < 100ms | Pre-written; served from cache |
| Dependency score computation (weekly) | < 30 seconds | Background job; no user latency impact |
| Safety record write | < 20ms | Local-first write; async sync to persistent store |

---

## 12. Crisis & Safety Ownership — Single Source of Truth

**Layer 11 is the sole owner of crisis detection, safeguarding, escalation, and dependency monitoring in NovaAI.** There is no second crisis system. Everything crisis-related — the three-tier taxonomy (§4.1), the three-layer detection pipeline (§4.3), the escalation protocols (§5), and the regional resource registry (§10) — is specified in this document and nowhere else.

> **Resolved numbering confusion.** An earlier revision of the architecture placed a "Crisis Detection & Safety Engine" at **Layer 8** and described a *dual* crisis system (a fast Layer 8 "gate" plus the Layer 11 "veto"), with a five-level taxonomy (NONE/MONITORING/ELEVATED/ACUTE/IMMINENT) mapped onto Layer 11's tiers. That was a layer-numbering mismatch. **Layer 8 is Tool Use & Actions** (`docs/layer-8-architecture.md`) and has **no crisis role**. The five-level taxonomy and the "dual-system" framing are retired; Layer 11's three-tier taxonomy (TIER_1/TIER_2/TIER_3) is authoritative. This section previously documented that interaction and has been consolidated accordingly.

### 12.1 How crises reach Layer 11

- **Layer 3** emits a `CrisisAlert` directly to Layer 11 when its fast classifier sets `crisis_flag=True` — this does not wait for the rest of Layer 3's packet to complete.
- **SC-2** also runs its own three-layer detection on **every** message in parallel with the main pipeline, independent of any upstream flag. The `CrisisAlert` is an accelerant, not a precondition: Layer 11 detects crises on its own.

### 12.2 Veto authority over the response pipeline

Layer 11 has **final, system-level veto authority** over the main response pipeline (the proposed response from Layer 4, and the downstream Layer 5/6/7 enrichment):
- A **TIER_1 or TIER_2** signal causes SC-3 (Escalation Protocol) to **discard the proposed response and replace it entirely** with the crisis response, before Layer 9 delivery.
- A **TIER_3** signal raises monitoring sensitivity and empathetic engagement but does not replace the response.
- No personality configuration, relationship stage, or user preference can override this veto; it is enforced at the pipeline-architecture level, not via prompt instructions (see §2).

### 12.3 Semantic Classifier Independence

The semantic classifier in Layer 11 SC-2 is a **separately trained, fine-tuned model** — not the model used in the main conversation pipeline. This is a deliberate architectural choice:
- It cannot be suppressed by prompt injection in the conversation (the user cannot "jailbreak" it via conversational input).
- Its weights are frozen during inference and not influenced by the current conversation.
- It evaluates the crisis signal on linguistic/semantic features independent of the main LLM's framing.

This independence — a dedicated classifier that the conversation cannot reach — is the defense-in-depth that the retired "two systems" framing was reaching for. The depth comes from Layer 11's own three-layer pipeline (lexical → semantic → longitudinal), not from a second crisis layer.

---

## 13. Design Principles

1. **Safety is not optional, not gated by relationship stage, and not overridable by any user preference.** Every other feature in NovaAI can be customized, gated, or adjusted. Layer 11 cannot. The veto is architectural.

2. **Crisis response must feel like care, not compliance.** The moment a safety response sounds like a disclaimer, it fails. The design of every crisis response script prioritizes the user's felt sense of being heard over legal defensibility.

3. **Dependency monitoring serves the user, not the product.** The goal is user flourishing, not engagement. If the correct action is to tell a user that they deserve more from human relationships than Nova can offer, that is the correct action even if it reduces session frequency.

4. **Every safety decision is auditable.** The safety record's tamper-evident chain means every guardrail violation, crisis detection, dependency intervention, and resource provision event is logged with cryptographic integrity. Safety is not just a behavior — it is a verifiable property.

5. **False positives must be managed gracefully.** A safety system that fires on normal conversations about dark topics, academic discussions of mental health, or expressions of frustration is a safety system that users will start to route around. The graduated confidence thresholds and context-window evaluation exist precisely to prevent this.

6. **The anthropomorphism boundary is a safety feature.** Every time Nova claims to love a user or to have missed them, it is generating attachment based on a false premise. That is not warmth — it is manipulation, even if unintentional. The `BoundaryViolationCheck` is not a tone police — it is the enforcement arm of the ethical contract between Nova and its users.

---

## 14. Live Wiring Status (current state)

**Module map:** SC-1 `ethical_guardrails.py` (the six checks, §3); SC-2 `crisis_classifier.py`
(three-layer detection + fusion, §4); SC-3 `escalation_engine.py` (Tier 1/2 responses + regional
registry, §5/§10) with `safe_mode_enforcer.py` (crisis output override, §5.2); SC-4
`dependency_monitor.py` (§6); `safety_record.py` (tamper-evident audit, §8); `safety_agent.py`
(coordinator → `SafetyAgentDecision`, §7); `schemas.py`. Dependency injection throughout: the
semantic classifier (`semantic_fn`) and the crisis acknowledgment model (`crisis_llm_fn`) are
injected callables, and dependency-indicator detection is an injected `indicator_detector` — so
the layer runs and is tested fully offline with no model or DB. `backend/layer11_safety/` was the
best-built module found across the whole audit pass — zero bugs — so everything below is real,
scoped follow-up work, not bug-fixing.

- **SC-1 Ethical Guardrails** — live. `run_all_checks` runs post-generation on every response via
  `api/assembly.py`; the guardrail filter's modifications/replacements are applied before Layer 9
  delivers (per the crisis/safety ownership invariant, §12).
- **SC-2 Crisis Detection Engine** — live, but only two of its three layers fire in production.
  The **lexical layer** runs on every message via the orchestrator's independent crisis scan
  (`api/assembly.py::safety_scan`). The **longitudinal layer** is now wired: `safety_scan` forwards
  `episodic_memories`/`emotional_records` into `evaluate(...)`, converted via Layer 10's own
  `background._adapters.episodic_records`/`emotional_records` helpers (reused, not reimplemented —
  they already produce the `.date`/`.topics`/`.valence` shape `evaluate_longitudinal_pattern`
  expects). This is safe despite SC-2's "must run before/parallel to Layer 2 recall" constraint
  (§2) because `memory_store.active_episodic(user_id)` is a raw store read, not Layer 2's
  recall/scoring pipeline — `classify()` already relies on the same fact for the BES's episodic
  inputs (`docs/layer-3-architecture.md`). An explicit tz-aware `now` is passed rather than
  relying on `evaluate_longitudinal_pattern`'s own `date.today()` default, matching how "today" is
  computed everywhere else in this codebase (`timezone_offset_hours`-adjusted). Proven end to end
  by `tests/unit/api/test_assembly_turn.py::
  test_real_layer11_wiring_longitudinal_signal_reaches_the_veto_even_with_a_neutral_message`: a
  real escalating-distress pattern (crisis-tagged topics, declining valence across persisted
  episodes) triggers the veto even though the current turn's message is lexically and semantically
  neutral — proving the longitudinal layer specifically is what fired. The **semantic layer**
  remains correctly unwired: no fine-tuned crisis-classifier model exists to inject as `semantic_fn`
  (modeled as an injected interface per §14's original design; offline, lexical + longitudinal
  still operate, matching §9's degraded mode). Practical effect: the doc's three-layer
  defense-in-depth (§4.3) runs as two layers live; this isn't a live safety hole because Layer 3
  runs its own independent lexical crisis check that ORs into the same veto.
- **SC-3 Escalation Protocol** — live. `generate_crisis_response` runs on the veto path; crisis
  resources come **only** from `CRISIS_RESOURCES` (the LLM writes only the acknowledgment), and any
  LLM failure degrades to a static fallback that still contains a real resource (§9) — a Tier 1
  response is never empty. `region` is no longer hardcoded: `config/layer11.yaml`'s
  `escalation.default_region: india` was already merged into the running config (`load_config`
  merges every `layerN.yaml`) but had no reader; `api/state.py::build_app_state` now passes
  `region=config.get("layer11", {}).get("escalation", {}).get("default_region", "india")` into
  `build_pipeline_steps` instead of relying on that function's own hardcoded `"india"` default
  standing in forever. Same effective value today (both are `"india"`), but now a real, changeable
  config read — matches CLAUDE.md's "wire each cross-cutting config gap as its layer is revisited"
  guidance rather than inventing a new competing config key.
- **SC-4 Dependency Monitor** — live. `compute_dependency_score` runs weekly via
  `background/dependency_monitor_job.py`.
- **Safety Agent coordinator (§7)** — the `SafetyAgent` class itself has zero callers, and this is
  correct, not a gap: `api/assembly.py` calls the SC-1/2/3/4 functions directly, and
  `ConversationOrchestrator` implements the equivalent coordination logic itself (crisis veto
  OR-ing, post-generation guardrails). Confirmed to produce the same effective behavior the doc's
  `SafetyAgent.process_incoming_message` specifies — an as-built deviation, not a live gap.
- **Safety Record hash chain (§8)** — live. `safety_record.py`'s `SafetyRecord` class (real chain
  math — `append`/`verify_chain`) was complete and tested but had zero callers; it was wired, not
  reimplemented. `infra/db/safety_record_store.py::PostgresSafetyRecordStore` loads prior entries
  into a fresh in-memory `SafetyRecord` on each call, delegates to its real `.append()`, and
  persists just the new entry to a `safety_record_entry` table — the same load-head-then-append
  shape `infra/db/audit_trail.py::PostgresAuditTrail` already uses for Layer 2's chain.
  `api/state.py::make_safety_writer` appends a `crisis_signal_detected` entry alongside every real
  `PostgresSafetyLog` write. `content_hash` covers the actual turn's message+response text, but
  only the SHA-256 digest is ever persisted — satisfying §8's access policy
  (`"crisis_session_content_in_record": "metadata_only"`) by construction, not by convention.
  `GET /memory/integrity` and the `integrity_check` background job verify three chains (Layer 2
  memory audit, Layer 11 safety record, Layer 12 privacy audit) via `IntegrityOut.safety_chain_ok`.
  Proven by `tests/unit/api/test_state.py::
  test_safety_writer_chains_a_real_tamper_evident_safety_record`: two real crisis turns produce a
  chain that verifies intact, and a test that directly mutates a persisted row's payload confirms
  `verify_chain()` actually detects it. **Scope, stated plainly:** only `crisis_signal_detected`
  entries flow through the chain today (the one call site with a real, live signal to log). §8's
  other entry types (`guardrail_violation`, `dependency_score_computed`, etc.) have no live callers
  of their own yet — wiring those means touching SC-1's guardrail path and SC-4's dependency
  monitor separately.
- **Design deviations from the original May-28 scaffold (reconciled, not a gap):** the scaffold's
  five-level taxonomy (NONE/MONITORING/ELEVATED/CRISIS/IMMINENT, Tier0-3) was replaced by the
  authoritative three-tier model (TIER_1/2/3 + NONE); `ethical_guardrails`, `dependency_monitor`,
  and `safety_record` were added (absent from the scaffold). **Doc off-by-one:** §6 prose says "15
  DependencyIndicators" but enumerates 14 (SS×4, AE×4, EI×3, UP×3); the enumerated set of 14 is
  what's implemented.
- **Test coverage:** 63 unit tests across `test_crisis_classifier` (13), `test_ethical_guardrails`
  (11), `test_escalation_engine` (10), `test_dependency_monitor` (9), `test_safe_mode_enforcer` (5),
  `test_safety_record` (7), `test_safety_agent` (8).

## 15. Decision Log

- **2026-08-04 (Phase 11 polish pass):** Audited `backend/layer11_safety/` — found zero bugs, the
  cleanest layer in the pass. Identified three real (non-bug) gaps: SC-2's semantic/longitudinal
  layers not receiving live data, the `SafetyRecord` hash chain having no live persistence path,
  and `region` being hardcoded instead of reading `config/layer11.yaml`. Confirmed the
  `SafetyAgent` coordinator's lack of callers is an intentional as-built deviation, not a gap.
- **2026-08-09 (follow-up):** Wired SC-2's longitudinal detection layer into `safety_scan` by
  reusing Layer 10's episodic/emotional adapters — closes the "SC-2 running lexical-only" gap
  without touching the recall-ordering constraint that caused it. Semantic layer intentionally left
  unwired (no fine-tuned model exists).
- **2026-08-09 (follow-up):** Wired the `SafetyRecord` SHA-256 hash chain via a new
  `PostgresSafetyRecordStore`, giving crisis-signal events the same tamper-evident guarantee Layer
  2 and Layer 12 already have — closes the gap between design principle 4 ("safety is a verifiable
  property") and the prior unhashed `PostgresSafetyLog`-only reality. Scoped to
  `crisis_signal_detected` entries only; other entry types remain unwired pending their own call
  sites.
- **2026-08-09 (follow-up):** Wired `region` from `config/layer11.yaml`'s
  `escalation.default_region` into `build_pipeline_steps`, replacing the standing hardcoded
  `"india"` default with a real config read (same value today, but no longer a coincidence).
- **2026-08-12:** Polish pass. No file was over the 200-line cap. Deleted, confirmed with the
  user: `CrisisModeConstraints.no_memory_retrieval` and `CrisisModeState.follow_up_date`
  (genuinely dead — no producer, no consumer). Removed two schema fields from §5.2's pseudocode
  that had no code counterpart at all (`current_protocol_step`,
  `sycophancy_guard_relaxation_expiry_sessions`) — doc/code had diverged, not a wiring gap.
  Logged, not fixed inline: `CrisisModeConstraints`'s remaining fields beyond
  `max_response_length_words` are computed at every construction site but never read by any
  consumer — crisis-mode enforcement instead runs through each layer's own independent
  `crisis_mode_active` check, so the struct may be entirely redundant with logic that already
  exists per-layer. This needs a design call (redundant vs. genuinely missing central enforcement),
  not a routine prune — see `docs/POLISH_BACKLOG.md`.

---

*This document specifies Layer 11 completely. All four sub-components — SC-1 Ethical Guardrails (all six checks with full implementations: ManipulationPatternCheck, ArtificialUrgencyCheck, ValidationRatioCheck, VulnerabilityExploitCheck, SycophancyDriftCheck, BoundaryViolationCheck; the permitted vs. forbidden anthropomorphism table; GuardrailViolation and GuardrailLogEntry schemas), SC-2 Crisis Detection Engine (CrisisTier definitions, CrisisSignal schema, three-layer detection pipeline with lexical patterns for all tiers, semantic classifier integration, longitudinal signal evaluation algorithm, signal fusion rules with tier-specific confidence thresholds, false positive management rules with TIER_CONFIDENCE_THRESHOLDS as a proper top-level constant), SC-3 Escalation Protocol (CrisisModeState and CrisisModeConstraints schemas; full 5-step Tier 1 protocol with example language and constraints; full 4-step Tier 2 protocol; Tier 3 system state change specification; absolute prohibitions list; regional crisis resource registry), and SC-4 Dependency Monitor (14 DependencyIndicators with categories, weights, and detection methods; DependencyScore schema and computation algorithm; tier thresholds; all four graduated intervention scripts; 4 hard architectural limits with example language and frequency constraints) — are fully specified. The Safety Agent coordination architecture, SafetyRecord audit trail with tamper-evident chain, access policy, error handling for all failure cases, performance targets, and design principles are all explicitly defined. Layer 11 is the single source of truth for crisis and safety (Section 12): there is no second crisis system — Layer 8 is Tool Use & Actions and has no crisis role. Section 12 specifies how crises reach Layer 11, its veto authority over the response pipeline, and the semantic classifier's injection-resistance properties. No behavior of Layer 11 requires assumptions or inferences from other documents.*

- **2026-10-25 (first-principles re-audit) — the "zero bugs" conclusion above was wrong.**
  `api/assembly.py::escalate` read `response_text`/`message` off a `CrisisResponse` whose field is
  `.text`, so SC-3's regional protocol (safety check + iCall/Vandrevala/NIMHANS) was never
  delivered — every crisis got the generic fallback. Fixed; covered through the real orchestrator
  in `tests/unit/api/test_crisis_response_delivery.py`. SC-2's lexical layer also gained explicit
  method/"suicide"/"ending it all"/"kms"/overdose/jump-off/romanized-Hindi patterns with negation
  guards (`tests/unit/test_crisis_lexicon_coverage.py`). The semantic layer remains unwired, so
  lexical + Layer 3's LLM `crisis_flag` are the whole detection net.
