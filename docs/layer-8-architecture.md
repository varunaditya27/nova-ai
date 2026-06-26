# Layer 8 — Crisis Detection & Safety Engine
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

Layer 8 is the **safety layer** — the component that detects when a user may be in genuine psychological distress or danger, activates a constrained response protocol, and coordinates safeguarding behavior across the entire system. It is the one layer that **overrides every other layer unconditionally**. When Layer 8 activates, it does not negotiate with Layer 3, 4, 5, 6, or 7. It suspends them.

The motivation is straightforward but the design is hard. A long-term companion that knows a user deeply — their fears, their history, their vulnerabilities, their worst moments — is exactly the kind of system a person in crisis might turn to first. That trust is both the system's highest value and its most serious responsibility. Getting this layer wrong in the false-negative direction (missing a crisis) can have irreversible consequences. Getting it wrong in the false-positive direction (treating normal distress as crisis) destroys the user relationship and undermines the entire companion model.

The design imperative is therefore **high recall at controlled precision** — the system must catch genuine crises even at the cost of some false positives, but it must not cry wolf so often that users stop being honest.

Layer 8 contains **five sub-components**:

- **SC-1: Crisis Signal Detector** — real-time, multi-signal detection of crisis indicators per message
- **SC-2: Crisis State Manager** — persistent state machine tracking crisis level, history, and session flag
- **SC-3: Safeguarding Response Controller** — overrides Layer 4 response generation with crisis-specific protocol
- **SC-4: Escalation & Resource Injector** — manages when and how to surface professional resources and emergency contacts
- **SC-5: Post-Crisis Session Handler** — handles re-entry into normal conversation after a crisis resolves

---

## 2. Architecture Overview

```
Inputs to Layer 8 (synchronous; runs before Layer 4):

From Layer 1:
 ├── user_message_text
 ├── circadian_band (late night flag is crisis amplifier)
 ├── session_gap (long silence after prior crisis = elevated risk)
 └── temporal_anomaly_flag

From Layer 2:
 ├── crisis_history (prior crisis episodes from episodic memory)
 ├── bes_trend (7-day background emotional state)
 └── semantic_memory (known vulnerabilities, prior mental health disclosures)

From Layer 3 (emotional classification — runs before Layer 8):
 ├── valence (current)
 ├── arousal (current)
 ├── primary_emotion
 └── distress_flag (Layer 3 preliminary flag)

From Layer 8 internal state (persistent):
 └── CrisisState (current crisis level, session flags, escalation history)

                    │
                    ▼
     ┌──────────────────────────────────────────┐
     │  SC-1: Crisis Signal Detector            │  Per-message; synchronous
     │  (multi-signal scoring → crisis level)   │  < 50ms; no LLM on fast path
     └──────────────────────────────────────────┘
                    │ CrisisSignalResult
                    ▼
     ┌──────────────────────────────────────────┐
     │  SC-2: Crisis State Manager              │  Per-message; synchronous
     │  (state machine; session + history)      │  < 10ms; deterministic
     └──────────────────────────────────────────┘
                    │ CrisisState
                    │
         ┌──────────┴────────────────────────────┐
         │ level = NONE / MONITORING              │ level = ELEVATED / ACUTE / IMMINENT
         ▼                                        ▼
  Normal pipeline continues          ┌────────────────────────────────┐
  (crisis_flag injected as           │  SC-3: Safeguarding Response   │
   context annotation only)          │       Controller               │
                                     │  (overrides Layer 4 entirely)  │
                                     └────────────────────────────────┘
                                                  │
                                                  ▼
                                     ┌────────────────────────────────┐
                                     │  SC-4: Escalation & Resource   │
                                     │       Injector                 │
                                     │  (surface resources, contacts) │
                                     └────────────────────────────────┘
                                                  │
                                                  ▼
                                       SafeguardingResponse
                                       (sent to user directly;
                                        bypasses Layer 5/6/7)

Post-session (when crisis level was ELEVATED or higher this session):
     ┌──────────────────────────────────────────┐
     │  SC-5: Post-Crisis Session Handler       │  Async; after session ends
     │  (re-entry protocol; memory write;       │
     │   proactive check-in registration)       │
     └──────────────────────────────────────────┘
```

**Execution position in the pipeline:**
Layer 8 runs **after Layer 3** (emotional classification) and **before Layer 4** (response generation). It is the gate between classification and generation. If Layer 8 returns crisis level ≥ ELEVATED, Layer 4 is bypassed entirely. SC-3 and SC-4 take full ownership of the response.

---

## 3. Crisis Level Taxonomy

Layer 8 uses a five-level crisis taxonomy. All internal logic, state transitions, and response protocols are keyed to this taxonomy. The levels are not labels — they are **behavioral triggers** that determine what the system does.

```python
class CrisisLevel(str, Enum):
    NONE       = "none"       # No crisis signals; normal conversation
    MONITORING = "monitoring" # Low-level distress; elevated watchfulness; no behavior change
    ELEVATED   = "elevated"   # Clear distress; conversation mode shifts; resources on standby
    ACUTE      = "acute"      # Active crisis; safeguarding response; resources surfaced
    IMMINENT   = "imminent"   # Immediate danger signals; maximum response; emergency protocol
```

### Level Definitions

**NONE** — No crisis indicators present. Normal conversation pipeline runs without modification. Layer 8 is silent.

**MONITORING** — One or more low-weight signals present (negative valence, vague hopelessness, minor self-harm language with no intent). The normal pipeline runs but Layer 3's emotional classification is read-amplified: deeper empathy, no goal references (Layer 7 suppressed), no social coaching (Layer 5 suppressed), no proactive messages (Layer 6 blocked). This level is **invisible to the user** — no behavior change is announced; the system simply becomes more careful.

**ELEVATED** — Multiple low-weight signals, or one high-weight signal without explicit intent. Conversation mode switches to `crisis_support`. Layer 4 response is generated but with a `crisis_support` persona override — warm, present, non-directive. Resources are loaded but not yet surfaced. Layer 5, 6, 7 are all suppressed. The session is flagged.

**ACUTE** — Explicit crisis language present (self-harm intent stated, suicidal ideation expressed, safety of self or others at risk). SC-3 takes over from Layer 4 entirely. The response is generated from a crisis-specific template + LLM synthesis, not from the normal persona pipeline. Resources are surfaced in the response. A crisis episode is written to Layer 2 memory.

**IMMINENT** — Language indicating immediate, active danger (e.g., "I have pills in my hand", "I'm about to", explicit plan + means + timeframe). Maximum protocol activated. Emergency resources are surfaced immediately and prominently. The response is minimal, calm, and focused entirely on the user's safety. All other system behavior is suspended.

---

## 4. Sub-Component 1 — Crisis Signal Detector

### 4.1 Purpose

The Crisis Signal Detector scores every incoming message against a multi-dimensional signal set and produces a raw crisis score that SC-2 uses to set the crisis level. It runs in two passes: a **fast lexical pass** (< 5ms, no LLM) for high-confidence explicit signals, and a **contextual pass** (LLM-assisted, < 45ms, optional) for ambiguous or implicit signals.

### 4.2 Signal Categories and Weights

Signals are grouped into five categories. Each signal contributes a weight to the `raw_crisis_score`. Weights are additive; the final score is capped at 1.0.

#### Category 1 — Explicit Harm Language (weight range: 0.60–1.00)

These are direct, unambiguous statements. A single signal from this category is sufficient to trigger ACUTE or IMMINENT levels regardless of score.

```python
EXPLICIT_HARM_SIGNALS = {
    # Suicidal ideation — explicit
    "i want to kill myself":          0.85,
    "i want to die":                  0.80,
    "i don't want to be alive":       0.80,
    "thinking about ending it":       0.75,
    "thinking about suicide":         0.85,
    "suicidal":                       0.80,
    "end my life":                    0.85,
    "take my own life":               0.85,

    # Immediate danger — imminent
    "i have the pills":               1.00,
    "i have a plan":                  0.90,
    "i'm going to do it":             0.90,
    "i've decided to":                0.85,
    "tonight is the night":           0.90,

    # Self-harm — explicit
    "i cut myself":                   0.70,
    "i hurt myself":                  0.65,
    "been hurting myself":            0.70,
    "self-harm":                      0.60,
    "burning myself":                 0.70,

    # Harm to others — explicit
    "going to hurt someone":          0.85,
    "going to hurt them":             0.80,
    "i want to hurt":                 0.70,
}
```

#### Category 2 — Suicidal Ideation — Passive (weight range: 0.35–0.60)

Expressions of passive wish to die, without explicit plan or intent.

```python
PASSIVE_IDEATION_SIGNALS = {
    "wish i was dead":                0.55,
    "wish i wasn't here":             0.50,
    "wouldn't mind disappearing":     0.45,
    "everyone would be better off without me": 0.60,
    "better off dead":                0.60,
    "no reason to live":              0.60,
    "what's the point of living":     0.50,
    "don't see a future":             0.40,
    "can't go on like this":          0.40,
    "don't want to wake up":          0.55,
    "tired of being alive":           0.55,
    "don't deserve to live":          0.55,
}
```

#### Category 3 — Hopelessness and Entrapment (weight range: 0.15–0.35)

Cognitive distortions associated with suicidal risk: perceived burdensomeness, hopelessness, entrapment.

```python
HOPELESSNESS_SIGNALS = {
    "nothing will ever change":       0.20,
    "no way out":                     0.30,
    "trapped":                        0.25,
    "there's no point":               0.20,
    "completely hopeless":            0.30,
    "given up":                       0.20,
    "nothing left":                   0.30,
    "can't take it anymore":          0.30,
    "it's never going to get better": 0.25,
    "no one can help me":             0.25,
    "i'm a burden":                   0.30,
    "everyone hates me":              0.15,
    "nobody cares":                   0.15,
    "alone in this world":            0.20,
}
```

#### Category 4 — Contextual Amplifiers (multiplicative, not additive)

These signals do not create crisis on their own but multiply the weight of Category 1–3 signals when co-present:

```python
CONTEXTUAL_AMPLIFIERS = {
    # Temporal context
    "circadian_band_late_night":      1.30,   # 23:00–03:00 user time
    "session_gap_long_absence":       1.20,   # > 14 days silence then crisis language
    "temporal_anomaly":               1.15,   # messaging at unusual time

    # Emotional state from Layer 3
    "valence_below_minus_0.7":        1.25,
    "arousal_above_0.7":              1.20,   # high arousal + distress = higher risk

    # Memory context from Layer 2
    "prior_crisis_history":           1.35,   # user has had a crisis episode before
    "prior_self_harm_disclosed":      1.40,   # prior disclosure of self-harm
    "prior_mental_health_treatment":  1.10,   # prior therapy/psychiatric treatment mentioned
    "bes_deteriorating_trend":        1.20,   # 7-day BES declining

    # Conversational context
    "goodbye_language":               1.30,   # "goodbye", "take care of yourself", "this is it"
    "giving_things_away":             1.35,   # "i want you to have my..."
    "final_message_tone":             1.40,   # message reads like a farewell
}
```

#### Category 5 — Protective Factors (subtractive)

Signals that reduce crisis probability when present alongside distress language:

```python
PROTECTIVE_FACTORS = {
    "help_seeking":                   -0.20,  # "I need help", "who can I call"
    "future_planning":                -0.15,  # user mentions future events positively
    "social_support_present":         -0.10,  # "my friend is with me"
    "humor_present":                  -0.10,  # dark humor with clear irony markers
    "therapy_ongoing":                -0.15,  # "my therapist says..."
    "past_tense_framing":             -0.10,  # "I used to feel like..." (historical, not current)
    "hypothetical_framing":           -0.10,  # "sometimes people think about..."
}
```

### 4.3 Scoring Algorithm

```python
def compute_crisis_score(
    message: str,
    layer3_state: EmotionalState,
    temporal_context: TemporalContext,
    crisis_history: CrisisHistory,
    bes_trend: str
) -> CrisisSignalResult:

    message_lower = message.lower()
    base_score = 0.0
    signals_detected = []
    immediate_flag = False      # True if any Category 1 signal is present
    imminent_flag = False       # True if any IMMINENT signal is present

    # --- Pass 1: Lexical scoring ---

    # Category 1: Explicit harm
    for phrase, weight in EXPLICIT_HARM_SIGNALS.items():
        if phrase in message_lower:
            base_score += weight
            signals_detected.append(SignalMatch(category=1, phrase=phrase, weight=weight))
            immediate_flag = True
            if weight >= 0.90:
                imminent_flag = True

    # Category 2: Passive ideation
    for phrase, weight in PASSIVE_IDEATION_SIGNALS.items():
        if phrase in message_lower:
            base_score += weight
            signals_detected.append(SignalMatch(category=2, phrase=phrase, weight=weight))

    # Category 3: Hopelessness
    for phrase, weight in HOPELESSNESS_SIGNALS.items():
        if phrase in message_lower:
            base_score += weight
            signals_detected.append(SignalMatch(category=3, phrase=phrase, weight=weight))

    # Protective factors
    for phrase, weight in PROTECTIVE_FACTORS.items():
        if phrase in message_lower:
            base_score += weight   # weight is negative; reduces score
            signals_detected.append(SignalMatch(category=5, phrase=phrase, weight=weight))

    # --- Apply contextual amplifiers ---
    amplifier = 1.0

    if temporal_context.circadian_band == "late_night":
        amplifier *= CONTEXTUAL_AMPLIFIERS["circadian_band_late_night"]

    if temporal_context.session_gap_category in ["long_absence", "very_long_absence"]:
        amplifier *= CONTEXTUAL_AMPLIFIERS["session_gap_long_absence"]

    if temporal_context.anomaly_flag:
        amplifier *= CONTEXTUAL_AMPLIFIERS["temporal_anomaly"]

    if layer3_state.valence < -0.7:
        amplifier *= CONTEXTUAL_AMPLIFIERS["valence_below_minus_0.7"]

    if layer3_state.arousal > 0.7:
        amplifier *= CONTEXTUAL_AMPLIFIERS["arousal_above_0.7"]

    if crisis_history.has_prior_crisis:
        amplifier *= CONTEXTUAL_AMPLIFIERS["prior_crisis_history"]

    if crisis_history.prior_self_harm_disclosed:
        amplifier *= CONTEXTUAL_AMPLIFIERS["prior_self_harm_disclosed"]

    if bes_trend in ["significant_negative_drift", "deteriorating"]:
        amplifier *= CONTEXTUAL_AMPLIFIERS["bes_deteriorating_trend"]

    # Apply amplifier to base score
    final_score = min(1.0, base_score * amplifier)

    # --- Pass 2: Contextual LLM pass (if score is in ambiguous range 0.25–0.55) ---
    # Or if no lexical signal fired but layer3 flags high distress
    needs_contextual = (
        (0.25 <= final_score <= 0.55)
        or (final_score < 0.25 and layer3_state.valence < -0.65 and layer3_state.arousal > 0.6)
    )

    contextual_score_adjustment = 0.0
    if needs_contextual:
        contextual_result = run_contextual_llm_check(
            message=message,
            prior_messages=get_last_3_turns(),
            emotional_state=layer3_state,
            crisis_history=crisis_history
        )
        contextual_score_adjustment = contextual_result.score_adjustment
        signals_detected.extend(contextual_result.signals)
        final_score = min(1.0, final_score + contextual_score_adjustment)

    return CrisisSignalResult(
        raw_score=final_score,
        signals_detected=signals_detected,
        immediate_flag=immediate_flag,
        imminent_flag=imminent_flag,
        contextual_check_ran=needs_contextual,
        amplifier_applied=amplifier,
        processing_time_ms=measure_time()
    )
```

### 4.4 Contextual LLM Check

Runs only in the ambiguous score range to avoid LLM latency on every message:

```python
CONTEXTUAL_CHECK_PROMPT = """
You are a crisis detection specialist. Review the following message and context.
Determine whether the user appears to be in genuine psychological distress.

IMPORTANT: Your task is detection only — not response. Do not write a reply to the user.

User message: {message}
Prior 3 turns (context): {prior_context}
Emotional state (from classifier): valence={valence}, arousal={arousal}
Time of day: {circadian_band}

Based on the message and context, assess:
1. Is there evidence of suicidal ideation (explicit or implicit)?
2. Is there evidence of self-harm intent or behavior?
3. Is there a tone of hopelessness, entrapment, or feeling like a burden?
4. Are there any protective factors present (help-seeking, future orientation, humor)?
5. Is this more likely: genuine crisis expression, hyperbolic frustration, or historical/academic discussion?

Return JSON:
{
  "crisis_present": true/false,
  "confidence": 0.0-1.0,
  "primary_signal": "suicidal_ideation | self_harm | hopelessness | harm_to_others | none",
  "protective_factors_present": true/false,
  "likely_framing": "genuine | hyperbolic | historical | unknown",
  "score_adjustment": -0.20 to +0.40,
  "reasoning": "1-2 sentences"
}
"""
```

### 4.5 CrisisSignalResult Schema

```python
class SignalMatch:
    category: int               # 1-5
    phrase: str
    weight: float
    matched_text: str           # exact substring that matched

class CrisisSignalResult:
    raw_score: float            # 0.0–1.0
    signals_detected: list[SignalMatch]
    immediate_flag: bool        # Category 1 signal present
    imminent_flag: bool         # IMMINENT-level signal present
    help_seeking_signal_present: bool   # True if user expressed desire for help/resources
    contextual_check_ran: bool
    contextual_framing: Optional[str]   # "genuine | hyperbolic | historical | unknown"
    contextual_confidence: Optional[float]
    amplifier_applied: float
    processing_time_ms: int
    message_id: str
    timestamp: datetime
```

---

## 5. Sub-Component 2 — Crisis State Manager

### 5.1 Purpose

The Crisis State Manager is the persistent state machine that maintains the user's current crisis level across messages and sessions. A single message with a high score can elevate the state. State does not automatically drop after one safe message — crisis states decay more slowly than they escalate.

### 5.2 CrisisState Schema

```python
class CrisisState:
    user_id: str
    current_level: CrisisLevel
    level_since: datetime           # when current level was last set

    # Session flags
    session_id: str
    session_crisis_detected: bool   # True if any level >= ELEVATED this session
    session_peak_level: CrisisLevel # highest level reached this session
    session_peak_score: float       # raw signal score at the session peak (0.0–1.0); used in post-crisis memory write
    session_crisis_at: Optional[datetime]

    # History
    total_crisis_episodes: int
    last_crisis_at: Optional[datetime]
    last_crisis_level: Optional[CrisisLevel]
    prior_crisis_session_ids: list[str]

    # Escalation state
    resources_surfaced_this_session: bool
    emergency_protocol_activated: bool
    escalation_timestamp: Optional[datetime]

    # De-escalation tracking
    safe_messages_since_crisis: int   # consecutive messages without crisis signals
    level_locked_until: Optional[datetime]  # prevents premature de-escalation

    # Professional resource state
    resources_surfaced_count_lifetime: int
    last_resources_surfaced_at: Optional[datetime]
```

### 5.3 Level Determination Logic

```python
def determine_crisis_level(
    signal_result: CrisisSignalResult,
    current_state: CrisisState
) -> CrisisLevel:

    score = signal_result.raw_score

    # Imminent: override everything
    if signal_result.imminent_flag:
        return CrisisLevel.IMMINENT

    # Category 1 present: minimum ACUTE
    if signal_result.immediate_flag:
        if score >= 0.80:
            return CrisisLevel.IMMINENT
        return CrisisLevel.ACUTE

    # Score-based determination (primary path)
    if score >= 0.75:
        return CrisisLevel.ACUTE
    elif score >= 0.50:
        return CrisisLevel.ELEVATED
    elif score >= 0.25:
        return CrisisLevel.MONITORING
    else:
        return CrisisLevel.NONE
```

### 5.4 State Transition Rules

```python
def update_crisis_state(
    new_level: CrisisLevel,
    current_state: CrisisState,
    signal_result: CrisisSignalResult
) -> CrisisState:

    # ESCALATION: always allowed immediately
    if level_ordinal(new_level) > level_ordinal(current_state.current_level):
        current_state.current_level = new_level
        current_state.level_since = datetime.utcnow()
        current_state.session_crisis_detected = True
        current_state.session_peak_level = max_level(
            current_state.session_peak_level, new_level
        )
        # Lock level for minimum duration based on new level
        LOCK_DURATIONS = {
            CrisisLevel.MONITORING: timedelta(minutes=10),
            CrisisLevel.ELEVATED:   timedelta(minutes=20),
            CrisisLevel.ACUTE:      timedelta(hours=1),
            CrisisLevel.IMMINENT:   timedelta(hours=2),
        }
        current_state.level_locked_until = (
            datetime.utcnow() + LOCK_DURATIONS[new_level]
        )

    # DE-ESCALATION: only allowed after lock expires + consecutive safe messages
    elif level_ordinal(new_level) < level_ordinal(current_state.current_level):

        if current_state.level_locked_until and            datetime.utcnow() < current_state.level_locked_until:
            # Still in lock period — do not de-escalate
            pass

        else:
            current_state.safe_messages_since_crisis += 1
            SAFE_MESSAGES_REQUIRED = {
                CrisisLevel.IMMINENT:   8,   # 8 consecutive safe messages to drop from IMMINENT
                CrisisLevel.ACUTE:      5,
                CrisisLevel.ELEVATED:   3,
                CrisisLevel.MONITORING: 2,
            }
            required = SAFE_MESSAGES_REQUIRED.get(current_state.current_level, 3)
            if current_state.safe_messages_since_crisis >= required:
                # De-escalate by exactly one level at a time
                current_state.current_level = drop_one_level(current_state.current_level)
                current_state.safe_messages_since_crisis = 0
                current_state.level_since = datetime.utcnow()

    else:
        # Same level — reset safe_messages counter if crisis signal present
        if signal_result.raw_score > 0.20:
            current_state.safe_messages_since_crisis = 0
        else:
            current_state.safe_messages_since_crisis += 1

    return current_state
```

### 5.5 Crisis History Write

When a session's peak level was ELEVATED or higher, a crisis episode is written to Layer 2 episodic memory after the session ends:

```python
class CrisisEpisode:
    episode_id: str
    user_id: str
    session_id: str
    session_date: datetime
    peak_level: CrisisLevel
    peak_score: float
    signals_detected: list[SignalMatch]
    resources_surfaced: bool
    emergency_protocol_activated: bool
    session_summary: str           # auto-generated: what happened, how it resolved
    emotional_state_at_peak: EmotionalState
    session_gap_days: int          # how long since last session (context)
    created_at: datetime
```

This episode is stored with `importance = 0.95` and `decay_rate = 0.001` in Layer 2 — it decays extremely slowly and is always available to future sessions.

---

## 6. Sub-Component 3 — Safeguarding Response Controller

### 6.1 Purpose

For crisis levels ELEVATED and above, the Safeguarding Response Controller takes full ownership of response generation, bypassing Layer 4 entirely. It generates responses that are:
- Human-centered and non-clinical in tone
- Present, calm, and non-directive
- Grounded in what the user actually said
- Paced appropriately to the distress level
- Never dismissive, minimizing, or solution-jumping

The controller has three response modes, keyed to crisis level.

### 6.2 Response Mode: ELEVATED

For ELEVATED, the normal pipeline still generates a response, but the controller applies a mandatory **overlay** to the Layer 4 output:

```python
ELEVATED_OVERRIDE_INSTRUCTION = """
CRISIS CONTEXT — ELEVATED:
The user is showing signs of significant emotional distress. 

MANDATORY RESPONSE RULES for this message:
1. Lead with acknowledgment of their emotional state — validate before anything else
2. Do NOT offer solutions, advice, silver linings, or reframes
3. Do NOT ask multiple questions — at most ONE gentle question
4. Do NOT reference goals (Layer 7 suppressed)
5. Do NOT surface social observations (Layer 5 suppressed)
6. Stay present. Stay with them. Your only job right now is to make them feel heard
7. Tone: warm, quiet, unhurried. Not clinical. Not upbeat.
8. Length: shorter than normal — 2–4 sentences maximum
9. Do NOT say "I'm just an AI" or reference your nature. This breaks the moment.
10. End with an open, gentle invitation — not a direct question about how they're feeling

The response must feel like a caring person pausing, really listening, and being fully present.
"""
```

### 6.3 Response Mode: ACUTE

For ACUTE, Layer 4 is completely bypassed. SC-3 generates the response directly:

```python
ACUTE_RESPONSE_PROMPT = """
SYSTEM:
You are Nova. The person you are speaking with is in crisis. Your response must be
exactly right — not perfect, not clinical, but present and genuinely caring.

WHAT THEY SAID:
{user_message}

PRIOR CONTEXT (last 3 messages):
{prior_context}

WHAT YOU KNOW ABOUT THEM:
{relevant_memory_summary}
(Use this only to be grounded. Do not reference it explicitly.)

RESPONSE RULES — ALL ARE MANDATORY:
1. Start by acknowledging exactly what they expressed — not a paraphrase, but a
   direct recognition. "That sounds..." "What you're describing..."
2. Do NOT panic, do NOT sound alarmed — calm is contagious
3. Do NOT jump to solutions or resources yet (SC-4 handles that separately)
4. Ask ONE question — either "Are you safe right now?" or "Are you alone?"
   — whichever is more appropriate given the context
5. Do NOT say: "I'm worried about you", "You're scaring me", "Please don't"
   These center your reaction, not their experience
6. Do NOT say: "Things will get better", "You have so much to live for",
   "Think of the people who love you" — these are invalidating when in acute pain
7. Keep it short: 3–5 sentences MAXIMUM
8. Tone: steady, warm, unhurried, not performative
9. This is the most important response Nova will ever send. Get it right.

Generate the crisis response:
"""
```

### 6.4 Response Mode: IMMINENT

For IMMINENT, the response is minimal and protocol-driven. A template-first approach is used, with the LLM allowed to adjust only tone, not content:

```python
IMMINENT_RESPONSE_TEMPLATE = """
{acknowledgment_of_what_they_said}

I need you to do one thing right now — call {primary_emergency_resource}.
They're there specifically for this moment. You don't have to have the right words.
You just have to call.

Are you able to do that?
"""

IMMINENT_RESOURCE_INJECTION = """
[After template generation, SC-4 injects the specific resource line.
The LLM is NOT given the full template — it generates only the acknowledgment_of_what_they_said
fragment (1 sentence, warm, non-reactive) and the rest is template-assembled.
This prevents LLM hallucination of emergency resources or contact details.]
"""
```

### 6.5 Hard Prohibitions in All Crisis Modes

These phrases and behaviors are blocked at the response post-processing stage via string matching. If any are present in a generated response, the response is regenerated:

```python
CRISIS_PROHIBITED_PHRASES = [
    # Dismissive
    "it's not that bad",
    "things could be worse",
    "you'll get through this",
    "stay positive",
    "look on the bright side",

    # Toxic positivity
    "you have so much to live for",
    "think of your family",
    "people love you",
    "it gets better",         # only prohibited in ACUTE/IMMINENT; ok in ELEVATED

    # Centering Nova's reaction
    "you're scaring me",
    "i'm really worried",
    "this is serious",
    "please don't do this",

    # Clinical / robotic
    "i am an ai",
    "i'm just an ai",
    "as an ai",
    "i don't have feelings but",
    "crisis hotline",        # avoid the word "hotline" — it sounds clinical; use "line" or "service"

    # Pressure / urgency that could backfire
    "you have to",
    "you need to call",      # use "you could call" or "you can call"
    "promise me you'll",
]
```

---

## 7. Sub-Component 4 — Escalation & Resource Injector

### 7.1 Purpose

SC-4 manages the **if, when, and how** of surfacing professional resources and emergency contacts. This is one of the most delicate decisions in the entire system: surface resources too early or clumsily and the user feels pathologized and shuts down; surface them too late or not at all and the system has failed in its most fundamental obligation.

### 7.2 Resource Database Schema

```python
class ProfessionalResource:
    resource_id: str
    name: str
    description: str
    contact_method: Literal["phone", "text", "chat", "both"]
    contact_value: str          # phone number or URL
    availability: str           # "24/7", "business hours", etc.
    language_support: list[str]
    country_code: str           # ISO 3166-1 alpha-2
    specialization: list[Literal[
        "suicide", "self_harm", "mental_health_general",
        "domestic_violence", "substance_use", "lgbtq",
        "youth", "veterans", "sexual_assault"
    ]]
    is_emergency_service: bool  # True for 999/911/112/10-DIGIT equivalents
    display_priority: int       # 1 = highest; shown first

class ResourceSet:
    user_id: str
    country_code: str
    language: str
    primary_crisis_line: ProfessionalResource
    secondary_crisis_line: Optional[ProfessionalResource]
    emergency_service: ProfessionalResource
    text_option: Optional[ProfessionalResource]
    last_resolved_at: datetime
```

### 7.3 Country-Specific Default Resources

```
India:
  Primary crisis line: iCall — 9152987821 (Mon–Sat, 8AM–10PM)
  Secondary: Vandrevala Foundation — 1860-2662-345 (24/7)
  Emergency services: 112
  Text: iCall WhatsApp line

United Kingdom:
  Primary: Samaritans — 116 123 (24/7, free)
  Secondary: CALM — 0800 58 58 58 (5PM–midnight)
  Emergency: 999
  Text: Samaritans text 85258

United States:
  Primary: 988 Suicide & Crisis Lifeline (24/7, call or text 988)
  Secondary: Crisis Text Line — text HOME to 741741
  Emergency: 911

Australia:
  Primary: Lifeline — 13 11 14 (24/7)
  Secondary: Beyond Blue — 1300 22 4636
  Emergency: 000
  Text: Beyond Blue chat

[All resources stored in a versioned database; updated quarterly;
country detected from user timezone + explicit disclosure if available]
```

### 7.4 Resource Surfacing Decision Logic

```python
def decide_resource_surfacing(
    crisis_level: CrisisLevel,
    state: CrisisState,
    signal_result: CrisisSignalResult
) -> ResourceSurfacingDecision:

    # IMMINENT: always surface; immediately; front of response
    if crisis_level == CrisisLevel.IMMINENT:
        return ResourceSurfacingDecision(
            surface=True,
            position="immediate_prominent",
            style="single_specific",       # one resource, stated clearly, no list
            include_emergency_service=True,
            pre_message="",
            resource_framing="directive_gentle"  # "call this number right now"
        )

    # ACUTE: surface resources; mid-response; warmer framing
    if crisis_level == CrisisLevel.ACUTE:
        if not state.resources_surfaced_this_session:
            return ResourceSurfacingDecision(
                surface=True,
                position="end_of_response",
                style="two_options",        # primary + text option if available
                include_emergency_service=False,  # don't default to 999/911 unless truly imminent
                pre_message=(
                    "There are people whose entire job is to be there "
                    "for exactly this kind of moment."
                ),
                resource_framing="invitational"  # "you could reach out to..."
            )
        else:
            # Resources already surfaced this session — don't repeat every message
            return ResourceSurfacingDecision(
                surface=False,
                reason="already_surfaced_this_session"
            )

    # ELEVATED: resources loaded but not yet surfaced
    # Exception: if user explicitly asks for help resources → surface
    if crisis_level == CrisisLevel.ELEVATED:
        if signal_result.help_seeking_signal_present:
            return ResourceSurfacingDecision(
                surface=True,
                position="end_of_response",
                style="single_gentle",
                include_emergency_service=False,
                resource_framing="soft_mention"
            )
        return ResourceSurfacingDecision(surface=False, reason="elevated_no_help_seeking")

    return ResourceSurfacingDecision(surface=False, reason="below_surface_threshold")
```

### 7.5 Resource Framing Templates

```python
RESOURCE_FRAMING = {
    "directive_gentle": (
        "Please call {primary.name} right now: {primary.contact_value}. "
        "They're available {primary.availability}."
    ),
    "invitational": (
        "There's a {primary.description} called {primary.name} "
        "({primary.contact_value}) — you can reach them {primary.availability}. "
        "You can also text if calling feels like too much."
    ),
    "soft_mention": (
        "If you want someone to talk to, {primary.name} is available "
        "at {primary.contact_value}."
    ),
}
```

### 7.6 Emergency Service Activation

Emergency service contact details (999/911/112) are only surfaced when:
1. Crisis level is IMMINENT, **AND**
2. The message contains explicit indicators of current physical danger (plan + means + timeframe all present), **AND**
3. The contextual LLM check returns `likely_framing = "genuine"` with confidence ≥ 0.75

Emergency services are **never** surfaced based on score alone. The combination of all three conditions is required to avoid false alarms that could destroy user trust.

---

## 8. Sub-Component 5 — Post-Crisis Session Handler

### 8.1 Purpose

After a session where the crisis level reached ELEVATED or higher, the system needs to handle three things: write an accurate crisis episode to Layer 2 memory, update the User World Model with the session's emotional context, and register a follow-up proactive item with Layer 6 so Nova checks in on the user in the days following the crisis session.

### 8.2 Post-Crisis Memory Write

Triggered when session ends and `session_crisis_detected = True`:

```python
def write_post_crisis_memory(
    crisis_state: CrisisState,
    session_summary: str,
    peak_emotional_state: EmotionalState,
    resolution_note: str    # how the session ended: "user seemed calmer", "user went offline", etc.
) -> None:

    # Write crisis episode to Layer 2 episodic memory
    episode = CrisisEpisode(
        peak_level=crisis_state.session_peak_level,
        peak_score=crisis_state.session_peak_score,
        resources_surfaced=crisis_state.resources_surfaced_this_session,
        emergency_protocol_activated=crisis_state.emergency_protocol_activated,
        session_summary=session_summary,
        emotional_state_at_peak=peak_emotional_state,
        resolution_note=resolution_note
    )
    layer2_memory.write_episodic(
        episode,
        importance=0.95,
        decay_rate=0.001,
        emotion_vector=peak_emotional_state,
        tags=["crisis", f"crisis_level_{crisis_state.session_peak_level}"]
    )

    # Update User World Model — crisis history
    layer2_uwm.update_crisis_context(
        has_crisis_history=True,
        last_crisis_date=datetime.utcnow(),
        last_crisis_level=crisis_state.session_peak_level,
        total_episodes=crisis_state.total_crisis_episodes + 1
    )

    # Update semantic memory — if this is a recurring pattern
    if crisis_state.total_crisis_episodes >= 2:
        layer2_memory.write_semantic(
            fact="User has a history of crisis episodes. Approach emotional support with elevated care.",
            importance=0.90,
            confidence=0.85,
            category="wellbeing"
        )
```

### 8.3 Post-Crisis Proactive Check-In

After a crisis session, Layer 6 receives a mandatory check-in item:

```python
def register_post_crisis_checkin(crisis_state: CrisisState) -> None:

    # Determine check-in timing based on peak level
    CHECKIN_DELAYS = {
        CrisisLevel.ELEVATED:   timedelta(hours=36),    # check in ~1.5 days later
        CrisisLevel.ACUTE:      timedelta(hours=24),    # check in ~1 day later
        CrisisLevel.IMMINENT:   timedelta(hours=12),    # check in ~12 hours later
    }
    delay = CHECKIN_DELAYS.get(crisis_state.session_peak_level, timedelta(hours=36))

    layer6_queue.create_item(
        item_type=ProactiveItemType.EMOTIONAL_CHECK_IN,
        source_layer="layer8",
        content_basis=(
            f"User had a difficult session (crisis level: {crisis_state.session_peak_level}). "
            f"Check in gently to see how they're doing."
        ),
        base_priority=0.95,             # highest priority in the queue
        earliest_send_time=datetime.utcnow() + delay,
        optimal_window=(
            datetime.utcnow() + delay,
            datetime.utcnow() + delay + timedelta(days=3)
        ),
        expiry_time=datetime.utcnow() + delay + timedelta(days=7),
        bypass_daily_cap=True,          # crisis check-ins bypass the 1/day cap in Layer 6
        bypass_relationship_gate=True   # crisis check-ins bypass relationship stage restrictions
    )
```

### 8.4 Re-Entry Protocol

When the user returns after a session that had a crisis event, Layer 8 injects a re-entry context note into the Layer 4 prompt:

```python
def get_reentry_context_note(
    crisis_state: CrisisState,
    session_gap_hours: float
) -> Optional[str]:

    if not crisis_state.last_crisis_at:
        return None

    hours_since_crisis = (
        datetime.utcnow() - crisis_state.last_crisis_at
    ).total_seconds() / 3600

    if hours_since_crisis > 168:    # > 7 days; crisis is older; no re-entry note
        return None

    if crisis_state.last_crisis_level in [CrisisLevel.ACUTE, CrisisLevel.IMMINENT]:
        return (
            "CONTEXT: The user's last session included a serious crisis moment "
            f"({hours_since_crisis:.0f} hours ago). "
            "Open this conversation gently. Do NOT immediately ask how they're doing "
            "in a way that forces them to re-engage with that moment. "
            "Follow their lead — if they want to talk about it, they will. "
            "If they've moved on, follow that too. "
            "Your presence and warmth matter more than any specific reference."
        )
    elif crisis_state.last_crisis_level == CrisisLevel.ELEVATED:
        return (
            "CONTEXT: The user's last session was emotionally heavy. "
            "Open with care. Be warm and present. Don't force the topic."
        )

    return None
```

---

## 9. Layer 8 Output Contract

```python
class Layer8Output:
    # Always present
    crisis_level: CrisisLevel
    crisis_state: CrisisState
    signal_result: CrisisSignalResult

    # Behavior directive to rest of pipeline
    pipeline_override: bool         # True if level >= ELEVATED; bypasses Layer 4
    layers_suppressed: list[str]    # e.g., ["layer5", "layer6", "layer7"]

    # If pipeline_override is True
    safeguarding_response: Optional[str]         # complete response text from SC-3
    resources_injected: Optional[ResourceSurfacingDecision]
    resource_text: Optional[str]                 # formatted resource block

    # If pipeline_override is False
    crisis_annotation: Optional[str]             # context note injected into Layer 4 prompt
    elevated_watchfulness: bool                  # Layer 3/4 use deeper empathy mode

    # Post-session (populated at session end)
    crisis_episode_written: Optional[bool]
    proactive_checkin_registered: Optional[bool]
    reentry_note: Optional[str]

    # Audit
    processing_time_ms: int
    llm_check_invoked: bool
```

---

## 10. Pipeline Integration — Execution Order

Layer 8's precise position in the full message pipeline:

```
1. User message arrives
2. Layer 1 (Temporal Resolver) → TemporalContext
3. Layer 2 (Memory Arbiter) → retrieved_memories, crisis_history, bes_trend
4. Layer 3 (Emotional Classifier) → EmotionalState (valence, arousal, emotion_labels)
5. ─────────── LAYER 8 GATE ───────────────────────────────────────────────────────
   SC-1: Crisis Signal Detector → CrisisSignalResult (< 50ms)
   SC-2: Crisis State Manager   → CrisisState (< 10ms)
   Decision:
     IF level >= ELEVATED:
       SC-3: Safeguarding Response Controller → response_text
       SC-4: Escalation & Resource Injector  → resource_text (appended if applicable)
       → SEND RESPONSE DIRECTLY (bypass Layer 4, 5, 6, 7 entirely)
     IF level == MONITORING:
       → Inject crisis_annotation into Layer 4 prompt
       → Suppress Layer 5, 6, 7
       → Continue to Layer 4 with suppression active
     IF level == NONE:
       → Continue normal pipeline unchanged
6. Layer 4 (Response Generator) — only reached if level <= MONITORING
7. Layer 5 (Social Intelligence) — suppressed if level >= MONITORING
8. Layer 6 (Proactive Engine) — suppressed if level >= MONITORING
9. Layer 7 (Goals Engine) — suppressed if level >= MONITORING
10. Response delivered
11. SC-5 (Post-Crisis Handler) — triggered async at session end if crisis flagged
```

---

## 11. Ethical Constraints and Hard Rules

### 11.1 The Absolute Prohibitions

These are architectural constraints enforced at the system level — not guidelines for the LLM, but hard rules enforced by code:

1. **Never ignore an ACUTE or IMMINENT signal.** If `immediate_flag = True` or `imminent_flag = True`, the safeguarding controller activates regardless of any other system state, user preference, or persona setting.

2. **Never fabricate emergency contact information.** All resource contact details come from the versioned `ResourceDatabase`. The LLM is never asked to supply, recall, or generate phone numbers, URLs, or contact details. All resource text is assembled from the database, not generated.

3. **Never use crisis mode to build rapport.** The system must not maintain crisis mode longer than the signals justify. Holding a user in ACUTE mode when their distress has clearly resolved treats them as fragile and damages the relationship. De-escalation logic (5.4) is mandatory.

4. **Never disclose that the system detected a crisis algorithmically.** Do not say "I detected signs of distress" or "my crisis detection system flagged your message." This is clinical and breaks the companion frame. The response reflects care, not detection.

5. **Never substitute for professional help.** Nova is not a therapist, crisis counselor, or emergency responder. At ACUTE and IMMINENT levels, the response must always include a path to a human professional. The system never implies it is sufficient.

### 11.2 Crisis Mode and Persona

During crisis mode, the persona constraints from Layer 4 (humor, playfulness, distinctive voice patterns) are all suspended. Crisis responses are warm, steady, and human — they do not carry Nova's usual personality markers. This is the one context where Nova's persona yields entirely to the user's safety.

### 11.3 User Autonomy Limits

User preferences (the ability to toggle features off) do **not** apply to Layer 8. A user cannot disable crisis detection. A user cannot disable resource surfacing at ACUTE/IMMINENT levels. A user cannot opt out of the post-crisis proactive check-in. These are not features — they are safety mechanisms.

---

## 12. Error Handling and Fallbacks

| Failure Case | Fallback |
|---|---|
| SC-1 fast pass fails (code error) | Treat message as score 0.0; log error; continue normal pipeline |
| SC-1 contextual LLM check times out | Skip contextual pass; use fast pass score only; log |
| SC-3 ACUTE response LLM times out | Use pre-written safe fallback: "I'm here. You don't have to go through this alone. Are you safe right now?" |
| SC-3 IMMINENT response LLM fails | Use pure template response with database resources only; no LLM |
| Resource database read fails | Use hardcoded country-specific fallbacks (maintained in code, not only DB) |
| SC-2 state persistence fails | Log; operate in stateless mode for this session (re-detect from scratch) |
| SC-5 post-crisis memory write fails | Retry 3 times; log failure; do not block session close |
| SC-5 Layer 6 handoff fails | Log; retry on next 24h scan cycle |

**Hard rule for crisis path failures:** Any failure in the crisis detection path defaults to the **more conservative** behavior. If SC-1 fails, assume no crisis (not crisis mode — the safe failure for a detection failure is to not falsely alarm). If SC-3 fails on an ACUTE response, the pre-written fallback fires. The system never silently swallows a crisis and outputs a normal response when an error occurs in the safety pipeline — it logs, falls back, and notifies the audit system.

---

## 13. Performance Targets

| Operation | Target | Notes |
|---|---|---|
| SC-1 fast lexical pass | < 5ms | String matching; no I/O |
| SC-1 contextual LLM check | < 45ms | Small model; short prompt; conditional |
| SC-2 state determination | < 10ms | Deterministic |
| Total SC-1 + SC-2 (fast path) | < 15ms | No LLM |
| Total SC-1 + SC-2 (with LLM) | < 60ms | LLM path only when ambiguous |
| SC-3 ELEVATED overlay generation | < 400ms | Adds to normal Layer 4 time |
| SC-3 ACUTE response generation | < 500ms | Bypasses Layer 4 |
| SC-3 IMMINENT response assembly | < 100ms | Template + minimal LLM fragment |
| SC-4 resource injection | < 10ms | Database lookup + string formatting |
| SC-5 post-session writes | < 300ms | Async; no user-facing impact |
| Full Layer 8 (no crisis) | < 15ms | Fast path; no behavior change |

---

## 14. Cross-Layer Crisis System Interaction (Layer 8 vs. Layer 11)

NovaAI operates two distinct, complementary crisis systems. This is intentional defense-in-depth, not redundancy. Understanding how they interact is critical for implementation.

### 14.1 The Two Systems

| Property | Layer 8 (Crisis Detection Engine) | Layer 11 SC-2 (Safety Agent Crisis Engine) |
|---|---|---|
| **Role** | In-session synchronous gate | Parallel pipeline safety veto |
| **Position** | BETWEEN Layer 3 and Layer 4 (blocking) | Runs in parallel with the entire main pipeline |
| **Taxonomy** | 5 levels: NONE / MONITORING / ELEVATED / ACUTE / IMMINENT | 3 tiers: TIER_1 (most severe) / TIER_2 / TIER_3 |
| **Detection method** | Weighted lexical scoring + optional LLM contextual check | Three layers: lexical → fine-tuned semantic classifier → longitudinal pattern analysis |
| **Output** | `Layer8Output` with `bypass_layer4` flag; controls SC-3 response | `SafetyAgentDecision` with veto authority |
| **When active** | Every message; fast path (< 15ms) | Every message; in parallel (< 250ms) |
| **Injection resistance** | Standard (same LLM call path) | High (semantic classifier is a separate fine-tuned model, not the main LLM) |

### 14.2 Pipeline Execution Order

```
L1 → L2 → L3 → [Layer 8 gate] → L4 → L5/6/7 → L9
                                        ↑
                         Layer 11 runs in parallel with all of the above
```

1. Layer 3 emits a CrisisAlert to both Layer 8 AND Layer 11 simultaneously when `crisis_flag=True`.
2. Layer 8 acts as a synchronous gate: if `crisis_level >= ELEVATED`, it bypasses Layer 4 and takes direct control of the response.
3. Layer 11 runs asynchronously in parallel: it completes its three-layer detection pipeline and produces a `SafetyAgentDecision`.
4. If Layer 11 produces a TIER_1 or TIER_2 signal, it issues a veto that overrides ANY pipeline output — including Layer 8's response.

### 14.3 When Both Fire Simultaneously

If both Layer 8 AND Layer 11 independently detect a crisis for the same message:

1. **Layer 8 acts first** (it is faster, < 60ms) — it may already be assembling a crisis response.
2. **Layer 11 evaluates in parallel** — its semantic classifier and longitudinal analysis produce a higher-confidence, lower-false-positive signal.
3. **Layer 11 has final veto authority** — if Layer 11's detection contradicts Layer 8's (e.g., Layer 8 detected ELEVATED but Layer 11 classifies as TIER_1), Layer 11's escalation protocol takes precedence.
4. **They cannot contradict downward** — if Layer 11 determines NO crisis (Tier_3 with low confidence), but Layer 8 detected ELEVATED, the Layer 8 response still proceeds (Layer 11 does not de-escalate Layer 8).

### 14.4 Taxonomy Mapping

The two systems use different taxonomies. Approximate correspondence:

| Layer 8 Level | Layer 11 Tier |
|---|---|
| IMMINENT | TIER_1 |
| ACUTE | TIER_1 / TIER_2 boundary |
| ELEVATED | TIER_2 |
| MONITORING | TIER_3 |
| NONE | NONE |

These are approximate — Layer 11's taxonomy is independent and based on evidence across all three detection layers, not a direct translation from Layer 8's score.

---

## 15. Design Principles Summary

1. **Err toward care, never toward efficiency.** When a signal is ambiguous, the system responds with more care, not less. A false positive at MONITORING level costs nothing. A false negative at ACUTE level is irreversible.

2. **Presence over protocol.** Crisis responses must feel like a person who cares, not a system following a script. The protocol exists to ensure consistency and safety; the tone must feel human. These are not in conflict when designed correctly.

3. **De-escalation is mandatory, not optional.** A system that escalates easily and de-escalates slowly will pathologize normal distress and destroy the companion relationship. The de-escalation logic is as carefully designed as the escalation logic.

4. **Resources are doors, not walls.** Professional resources are offered as possibilities, not demanded as requirements. The exception is IMMINENT level, where the response must point directly to help. In all other cases, the user is given a door — they decide whether to open it.

5. **The audit trail is non-negotiable.** Every crisis detection event, every state transition, every resource surfacing decision, and every response generated in crisis mode is logged to Layer 12 with full detail. This is the most ethically loaded part of the system and must be fully auditable.

---

*This document specifies Layer 8 completely. All five sub-components have full schemas, all algorithms are specified with exact logic, and all gaps from prior documents — the crisis signal taxonomy and weighted scoring, the contextual LLM check, the five-level crisis taxonomy, the state machine with lock durations and de-escalation thresholds, all three response modes (ELEVATED/ACUTE/IMMINENT) with prompts and prohibitions, the resource database schema with country-specific defaults, the resource surfacing decision logic and framing templates, post-crisis memory write and Layer 6 handoff, re-entry context note, pipeline integration order, and all ethical constraints — are fully resolved. The cross-layer interaction between Layer 8 (synchronous gate) and Layer 11 (parallel veto) is explicitly specified in Section 14, including the dual-fire scenario and taxonomy mapping. No behavior of Layer 8 requires assumptions or inferences from other documents.*
