# Layer 1 — Input Perception
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

Every message Nova receives is not just a string of text. It is an **event** — with a timestamp, a behavioral history behind it, a set of signals about how it was sent, and a modality that may carry meaning beyond the words themselves. Layer 1 is the pipeline that transforms that raw event into a rich, structured context object before any reasoning, memory retrieval, or response generation happens.

The foundational claim of this layer is:

> **The same message means different things depending on when it arrived, how long the silence was before it, how it was typed, and what form it came in.**

*"I messed up again"* at 11 PM after a 12-day silence is a crisis signal. The same words at 3 PM in the middle of an ongoing conversation is casual venting. A pure text model sees identical input. Layer 1 is what makes Nova see the difference.

Layer 1 runs **before any other agent**. It produces a single, read-only `InputPerceptionPacket` that every downstream layer consumes. No downstream agent re-derives temporal logic, re-classifies implicit signals, or re-normalizes multimodal input independently. This is the contract.

---

## 2. Architecture Overview

Layer 1 contains **five sub-components** that run in a strict pipeline sequence:

```
Raw Incoming Event
        │
        ▼
┌─────────────────────────────┐
│  SC-1: Temporal Resolver    │  (deterministic, zero LLM calls)
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  SC-2: Implicit Signal      │  (deterministic signal extraction)
│        Extractor            │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  SC-3: Multimodal           │  (conditional — fires only on non-text input)
│        Normalizer           │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  SC-4: Voice Prosody        │  (conditional — fires only on voice input)
│        Extractor            │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  SC-5: Input Perception     │  (assembles all sub-component outputs
│        Assembler            │   into one unified packet)
└─────────────────────────────┘
        │
        ▼
  InputPerceptionPacket
  (read-only, passed to all downstream layers)
```

The pipeline is almost entirely **deterministic and zero-LLM**. SC-3 and SC-4 each invoke a single lightweight vision or audio model only when the relevant modality is present. Total execution time target: **under 5ms** for text-only messages, under **100ms** for multimodal messages.

---

## 3. Sub-Component 1 — Temporal Resolver

### 3.1 Purpose

The Temporal Resolver answers the question: **when is this message, relative to everything we know about this user and this conversation?**

It maps the raw timestamp to a structured set of temporal signals — circadian position, session gap, behavioral anomaly, fuzzy memory labels, and due narrative threads. Every downstream agent reads these signals; none re-derives them.

### 3.2 Wall-Clock Mapping and Circadian Bands

Each incoming message is mapped to a circadian band based on the user's local time (inferred from timezone, set during onboarding or inferred from message timestamp patterns).

| Band | Local Time | Behavioral Prior | Default Conversational Posture |
|------|-----------|------------------|-------------------------------|
| `late_night` | 23:00–03:00 | High emotional vulnerability; impulsive messaging; potential loneliness or insomnia | Soft tone, validation-first, no task assignment, heightened crisis sensitivity |
| `early_morning` | 03:00–06:00 | Unusual wakefulness; anxiety-driven; urgent concerns | Same as late_night + explicit gentle acknowledgement of atypical timing |
| `morning` | 06:00–12:00 | Task-oriented, alert, planning mode | Concise, practical, direct. Good window for goal-related content |
| `afternoon` | 12:00–17:00 | Mid-flow, relatively neutral, flexible | Match user's lead; no forced posture |
| `evening` | 17:00–21:00 | Decompression, social reflection, higher relational openness | Warm, reflective, good window for checking long-running threads |
| `night` | 21:00–23:00 | Wind-down; emotionally open before sleep | Thoughtful, unhurried, no pressure to resolve everything |

The circadian band is one of the most consistently mishandled signals in existing AI assistants. Nova responds differently to "I can't sleep" at 2:30 AM than to the same message at 2:30 PM — not just in content but in posture.

**The `circadian_mood_prior`** is a float in `[0, 1]` computed from the band and any known user-specific deviations (see §3.4). It represents the estimated probability that the user is in an emotionally vulnerable state, used by Layer 3 (Emotion Refiner) as a Bayesian prior before reading the message content:

```
late_night     → 0.75
early_morning  → 0.80
morning        → 0.20
afternoon      → 0.25
evening        → 0.40
night          → 0.55
```

These are population-level defaults. They update per-user over time (see §3.4).

### 3.3 Session Gap Classification

The gap since the user's last message (or last session end, defined as 30+ minutes of inactivity) is classified into seven qualitative buckets. Each maps to a distinct re-entry behavioral policy.

| Gap Category | Duration | Human-Readable Label | Re-Entry Behavior |
|---|---|---|---|
| `same_session` | 0–30 min | *"just now"* | Continue as if in one thread; no explicit re-entry |
| `short_break` | 30 min–4 hrs | *"a little while ago"* | Natural re-entry; light recap if contextually relevant |
| `same_day` | 4–24 hrs | *"earlier today / this morning"* | Mild acknowledgment; check on unresolved threads from earlier |
| `few_days` | 1–3 days | *"a couple of days ago"* | Gentle check-in on pending threads; don't assume emotional continuity |
| `week_or_two` | 4–14 days | *"about a week ago"* | Acknowledge gap; surface highest-priority thread; invite update |
| `long_absence` | 15 days–3 months | *"a while back"* | Warm reconnect; broad check-in; no drilling into old specifics unless user initiates |
| `very_long_absence` | 3+ months | *"it's been a long time"* | Near-reacquaintance; treat as reconnecting with long-unseen friend; stable knowledge of user, low confidence in current events |

The `session_gap_seconds` (raw) and `gap_category` (enum) are both stored in the output packet. The `human_readable_gap_label` is the fuzzy string Nova uses in language — never the raw number.

**Gap-driven opening logic** (consumed by Layer 4, Persona Enforcer):

- `same_session` / `short_break` → continue topic seamlessly
- `same_day` → weave in light acknowledgment + any due threads
- `few_days` / `week_or_two` → explicit gap recognition + thread check
- `long_absence` / `very_long_absence` → explicit reconnect opener; let user steer relevance of old threads

### 3.4 User-Specific Temporal Pattern Modeling

The Temporal Resolver maintains a per-user behavioral baseline that enables anomaly detection. This baseline is updated after each session.

**Tracked statistics per user:**

```python
class UserTemporalProfile:
    user_id: UUID
    timezone_offset_hours: float          # inferred or explicitly set
    typical_bands: dict[str, float]        # band → frequency (0–1), e.g. {"evening": 0.62}
    average_session_frequency_days: float  # rolling 90-day average
    typical_session_duration_minutes: float
    longest_historical_gap_days: float
    last_session_end: datetime
    total_sessions: int
    relationship_age_days: int             # days since first conversation
    per_band_circadian_prior: dict[str, float]  # personalized, overrides defaults after 20+ sessions
```

**Anomaly detection logic:**

An anomaly flag is set when any of the following conditions are true:

1. The current message falls in a band that accounts for less than 5% of the user's historical messages (atypical time)
2. The session gap exceeds `average_session_frequency_days × 2.5`
3. The gap is shorter than 10% of the shortest gap in the rolling 30-day history (unusually rapid return — possible distress or high engagement)

When an anomaly is detected, a `context_note` string is generated for downstream agents:

- *"User messaging at 2:10 AM — atypical (usually messages 7–10 PM)"*
- *"First contact in 19 days — baseline is every 3–4 days"*
- *"Second session today — unusually rapid return"*

The `context_note` is a plain-language string. It is **not** a conclusion about emotional state — it is a signal flag for Layer 3 to interpret.

### 3.5 Pending Thread Surfacing

Narrative threads — open loops from previous conversations that warrant follow-up — are stored in a `ThreadStore` (defined in Layer 2 / State Updater). At the start of each session, the Temporal Resolver queries which threads are due.

**Thread object schema:**

```python
class NarrativeThread:
    thread_id: UUID
    summary: str                    # "Job interview scheduled for Thursday"
    created_at: datetime
    follow_up_due_at: datetime
    status: Literal["unresolved", "resolved", "expired", "snoozed"]
    emotional_weight: float         # 0–1; influences surfacing priority
    importance_tier: Literal["critical", "high", "medium", "low"]
    thread_type: Literal[
        "future_event",             # interview, exam, appointment
        "emotional_situation",      # ongoing conflict, grief, anxiety
        "intention_commitment",     # "I'll try talking to my manager"
        "chronic_context",          # long-term family tension, recurring health issue
        "factual_pending"           # "waiting on results / decision"
    ]
    snooze_until: Optional[datetime]
    source_session_id: UUID
```

**Follow-up scheduling policy by thread type:**

| Thread Type | Follow-up Window | Rationale |
|---|---|---|
| `future_event` | 12–24 hrs after event | After it's happened; close enough to still feel relevant |
| `emotional_situation` | 3–5 days after creation | Enough time to breathe; not so long it feels forgotten |
| `intention_commitment` | 7 days after creation | Let the user act; check in after reasonable window |
| `chronic_context` | 14–21 days | Recurring; not every session, but kept alive |
| `factual_pending` | 2–3 days, or when result-related keywords surface | Results often arrive quickly; watch for topic re-emergence |

**Surfacing logic:**

```python
def get_due_threads(thread_store, now: datetime, max_threads: int = 2) -> list[NarrativeThread]:
    candidates = [
        t for t in thread_store.get_all(status="unresolved")
        if t.follow_up_due_at <= now and (t.snooze_until is None or t.snooze_until <= now)
    ]
    # Sort by composite priority: emotional_weight * importance_tier_score
    return sorted(candidates, key=lambda t: priority_score(t), reverse=True)[:max_threads]
```

At most **2 threads** are surfaced per session. Both are included in the output packet; Layer 6 (Proactivity) decides which one to lead with in the conversation opener, based on emotional register and context.

### 3.6 Fuzzy Temporal Labeling

All timestamps stored in Layer 2 memory are **absolute** (ISO 8601). At retrieval time, the Temporal Resolver converts them to fuzzy, human-relative labels. The LLM never sees a raw timestamp.

**Mapping table:**

| Age of Memory | Label |
|---|---|
| < 30 minutes | *"a moment ago"* |
| 30 min–4 hrs | *"earlier today"* |
| 4–24 hrs | *"yesterday"* / *"earlier today"* (context-dependent) |
| 1–3 days | *"a couple of days ago"* |
| 4–7 days | *"earlier this week"* |
| 8–14 days | *"about a week ago"* |
| 15–30 days | *"a few weeks ago"* |
| 31–60 days | *"last month"* |
| 2–4 months | *"a couple of months ago"* |
| 4–8 months | *"a while back"* |
| 8–14 months | *"earlier this year"* / *"back in [month]"* |
| 14–24 months | *"about a year ago"* |
| 2+ years | *"a couple of years ago"* / *"back in [year]"* |

**Language policy (enforced downstream in Layer 4):**

- Always use fuzzy labels, never ISO dates or phrases like *"according to my records"*
- Combine temporal label with emotional continuity: *"you mentioned a few weeks ago that... how does that feel now?"*
- Never refer to memory timestamps in a way that reveals a database operation

---

## 4. Sub-Component 2 — Implicit Signal Extractor

### 4.1 Purpose

Implicit signals are the **metadata of how a message was sent**, not what it says. This sub-component addresses the most underused signal class in conversational AI. The irony in the existing design is stark: Layer 9 (Output Orchestrator) generates typing latency, deletion behavior, and backchannels as *output* to simulate humanness — but the equivalent signals arriving *inbound* from the user were completely unread. That asymmetry is now corrected.

Implicit signals are not about what the user said. They are behavioral fingerprints that carry emotional and intentional meaning that text content alone cannot.

### 4.2 Signal 1 — Message Latency

**Definition:** Time elapsed between Nova delivering its previous message and the user beginning to type (or sending) this one.

**Capture mechanism:** The client records a `nova_delivered_at` timestamp when Nova's message renders and a `user_typed_at` timestamp when the user sends. The delta is `response_latency_ms`.

**Interpretation schema:**

| Latency | Interpretation | Signal Label |
|---|---|---|
| < 3 seconds | Reactive, not reflective; emotional or impulsive response | `reactive` |
| 3–15 seconds | Quick reply; engaged but not deeply considered | `quick` |
| 15–60 seconds | Normal considered reply | `considered` |
| 1–5 minutes | Paused and thought; topic may have required reflection | `reflective` |
| 5–20 minutes | Significant pause; possibly looked something up, stepped away briefly | `delayed` |
| > 20 minutes | Session break; treat as new sub-session | `break` (triggers re-entry posture) |

**Important:** Latency is interpreted relative to the message it follows. A 5-second response to *"what's 2+2"* is normal. A 5-second response to *"I've been thinking about ending things"* is reactive-alarming. The latency value is passed to Layer 3 (Emotion Classifier) which contextualizes it against message content.

**User-specific calibration:** Each user's baseline latency is tracked as a rolling median over the last 50 messages. Deviations from baseline (> 3× or < 0.3×) are flagged in the signal, not just the absolute value.

### 4.3 Signal 2 — Edit/Deletion Behavior

**Definition:** Did the user type content and then delete it before sending?

**Capture mechanism:** The client sends a `deletion_event` flag when the user's outbound message was edited at least once before sending (detectable via typing event stream on the client side — a message buffer that tracks start-typing, clear, resume-typing sequences without capturing the deleted content).

**What is captured:**
- `deletion_occurred: bool` — did any deletion happen?
- `deletion_count: int` — how many times did the user start-over or partially delete?
- `final_length_vs_peak_length_ratio: float` — how much shorter is the sent message than the longest draft? (e.g., 0.2 means they wrote 5× what they sent)

**What is NOT captured:** The content of deleted text is never recorded. Only behavioral metadata.

**Interpretation:**

| Pattern | Interpretation |
|---|---|
| Single minor deletion | Normal self-correction, no signal |
| 2–3 deletions, ratio > 0.5 | Deliberate self-censorship; user started to say something and chose not to |
| High deletion count (4+), ratio < 0.3 | Significant internal conflict; multiple attempts to articulate something difficult |
| Complete clear-and-restart pattern | User abandoned one framing entirely; second framing represents chosen disclosure |

Self-censorship is one of the most valuable signals available. When a user clearly wrote a lot, deleted most of it, and sent something brief — they were protecting something. Layer 3 treats this as an intimacy signal: the user may be holding back something emotionally significant. Nova's response posture should create space rather than fill it.

### 4.4 Signal 3 — Message Length Distribution

**Definition:** The length (in characters) of the current message, interpreted relative to the user's historical baseline.

**Tracked statistics:**
- `baseline_message_length_chars`: rolling median of last 100 messages
- `current_message_length_chars`: length of this message
- `length_ratio`: `current / baseline` — the deviation signal

**Interpretation:**

| Length Ratio | Interpretation |
|---|---|
| < 0.2 | Unusually short (e.g., baseline is 80 chars, sent 10 chars) — withdrawal, flat affect, or clipped response |
| 0.2–0.5 | Shorter than normal — possibly distracted, tired, or disengaged |
| 0.5–2.0 | Normal range |
| 2.0–4.0 | Longer than usual — elaborating, processing something complex or emotional |
| > 4.0 | Significantly longer than baseline — high investment; venting; unloading; something important |

Message length is a well-documented proxy for emotional processing load. Humans write more when working through something difficult. They write less when they're shutdown, distracted, or simply done.

### 4.5 Signal 4 — Session Initiation Type

**Definition:** Did the user start this conversation unprompted, or are they responding to a Nova check-in/proactive message?

**Categories:**

| Initiation Type | Description | Interpretation |
|---|---|---|
| `user_initiated_cold` | User opened Nova with no prior proactive message | User has something on their mind; readiness to engage is high |
| `user_initiated_hot` | User re-opened after recent Nova proactive message | User responded to a check-in; engagement may be reactive |
| `response_to_checkin` | User is directly replying to Nova's proactive reach-out | Cooperative engagement; check-in landed well |
| `continuation` | Session gap < 30 min; ongoing conversation | Same thread; no re-entry needed |

This signal affects Layer 6 (Proactivity Engine) feedback loop — whether a proactive check-in resulted in a user-initiated follow-on is a training signal for the Intrusion Cost Model.

### 4.6 Signal 5 — Consecutive Message Burst

**Definition:** Did the user send multiple messages in rapid succession without Nova responding between them?

**Capture mechanism:** If more than one message arrives within a 45-second window before Nova responds, they are bundled as a `message_burst` with:
- `burst_count: int` — number of messages in the burst
- `burst_total_length_chars: int`
- `avg_inter_message_gap_seconds: float`

**Interpretation:** A burst of 3–5 short messages often indicates the user is processing something emotionally in real time — thinking out loud, streaming consciousness. Nova should read the burst holistically, not respond to each message individually. The full burst context is passed as a unit to downstream layers.

### 4.7 The Implicit Signal Score

All five implicit signals are aggregated into a single `implicit_emotional_intensity_score` (float 0–1) that gives Layer 3 a pre-linguistic estimate of emotional load before reading the message content:

```python
def compute_implicit_emotional_intensity(
    latency_signal: str,
    deletion_occurred: bool,
    deletion_count: int,
    length_ratio: float,
    initiation_type: str
) -> float:
    score = 0.0

    # Latency contribution
    latency_weights = {"reactive": 0.6, "quick": 0.2, "considered": 0.0,
                       "reflective": 0.1, "delayed": 0.2, "break": 0.0}
    score += 0.25 * latency_weights.get(latency_signal, 0.0)

    # Deletion contribution
    if deletion_occurred:
        score += 0.20 * min(deletion_count / 5.0, 1.0)

    # Length deviation contribution
    if length_ratio > 4.0:
        score += 0.25 * min((length_ratio - 4.0) / 4.0, 1.0)
    elif length_ratio < 0.2:
        score += 0.20  # withdrawal signal

    # Initiation contribution
    if initiation_type == "user_initiated_cold":
        score += 0.10  # user chose to come; something is on their mind

    return min(score, 1.0)
```

This score is **not** a diagnosis. It is a weighted pre-signal that shifts Layer 3's emotional prior before any content analysis. At score 0.0, Layer 3 starts neutral. At score 0.8+, Layer 3 enters the message expecting significant emotional content and calibrates accordingly.

---

## 5. Sub-Component 3 — Multimodal Normalizer

### 5.1 Purpose

In a real messaging interface, users send more than text. Images, voice notes, documents, screenshots, location pins, and files are everyday inputs. Nova cannot respond meaningfully to *"look at this"* without understanding what "this" is. This sub-component normalizes all non-text modalities into a structured `ModalityContext` that the rest of the pipeline can consume as if it were a text-compatible semantic description.

**The architectural principle:** All modalities are normalized to text-compatible semantic representations before entering Layer 2 onward. No downstream agent handles raw binary data. The Multimodal Normalizer is the sole entry point for non-text input.

### 5.2 Supported Modalities

| Modality | Input Format | Normalizer Model | Output |
|---|---|---|---|
| Image (photo, screenshot, meme) | JPEG/PNG/WEBP | LLaVA-1.6 7B (on-device) or GPT-4o Vision (cloud, opt-in) | Semantic description + detected text (OCR) + inferred emotional context |
| Voice note | M4A/OGG/MP3 | Whisper.cpp (on-device, small model) | Transcript + prosody features (see SC-4) |
| Document (PDF, DOCX) | File attachment | Apache Tika → plaintext extraction | Extracted plaintext + metadata (title, page count, key headings) |
| Location pin | Lat/Lon + place name | Reverse geocoding (offline-capable) | Semantic description: "Home area", "University campus", "New location — not seen before" |
| Short video | MP4, < 60s | Frame sampling (5 fps) → LLaVA on keyframes | Scene description + transcript if speech present |
| Reaction / emoji | Reaction event | Direct mapping | Mapped to emotion label: ❤️ → `affection_signal`, 😂 → `amusement_signal` |
| File (generic) | Any file type | MIME type detection → metadata only | File type + name + size; content not processed unless explicitly supported |

### 5.3 Image Normalization Detail

Images carry multiple signal types simultaneously. The normalizer extracts:

**Visual content description:** What is in the image? (Objects, people, scenes, text visible on screen — OCR output.)

**Emotional context inference:** What emotional register does the image carry? A screenshot of a rejection email is different from a photo of a sunset. This is a brief inference (1–2 sentences), not a deep interpretation.

**Image type classification:**

| Image Type | Downstream Behavior Implication |
|---|---|
| Screenshot (app/web content) | May contain important text; run OCR; treat as informational input |
| Personal photo (faces, people) | Privacy-sensitive; describe without identifying; note people present |
| Meme / reaction image | Treat as emotional expression; interpret cultural register |
| Document photo | Extract visible text; OCR priority |
| Ambient/environmental photo | Describe context; infer mood/situation |

**Privacy constraint:** Face recognition is explicitly disabled. The normalizer detects *"people present in image"* (count and approximate age range) but does not attempt identification. This is a hard constraint, not a configurable setting.

### 5.4 Voice Note Normalization Detail

Voice notes pass through both SC-3 (for transcript) and SC-4 (for prosody). SC-3 is responsible only for the transcript.

**Transcription pipeline:**

1. Audio arrives as M4A/OGG
2. Whisper.cpp small model (runs on-device in < 2 seconds for notes under 60s) produces transcript
3. Transcript is passed to main text pipeline as if typed
4. Raw audio is retained in memory (RAM only, not persisted to disk) for the duration of the SC-4 prosody pass
5. Raw audio is discarded after SC-4 completes — only the transcript and prosody features persist

**Language detection:** Whisper auto-detects language. If the user speaks in a language different from their established primary, this is flagged as a `language_switch_event` — a culturally significant signal (some users switch language under emotional intensity).

### 5.5 Document Normalization Detail

Documents are normalized differently depending on their likely purpose:

- **Academic documents** (syllabus, paper, assignment): Extract title, headings, and key deadlines/dates
- **Professional documents** (offer letter, contract, report): Extract key named entities, monetary figures, dates
- **Personal writing** (diary, notes, drafts): Full-text extraction; treat as high-intimacy disclosure
- **Technical documents** (code files, specs): Full-text extraction; note language/technology context

The output is always a `DocumentSummary` object:

```python
class DocumentSummary:
    document_type: str                   # academic, professional, personal, technical, unknown
    title: Optional[str]
    extracted_text: str                  # full text (up to 10,000 chars)
    key_dates: list[str]                 # ISO dates found in document
    key_entities: list[str]              # names, organizations, amounts
    estimated_emotional_significance: float  # 0–1; personal writing = high; syllabus = low
```

### 5.6 Output: ModalityContext

```python
class ModalityContext:
    primary_modality: Literal["text", "image", "voice", "document", "location", "video", "reaction", "mixed"]
    text_content: Optional[str]              # transcribed/extracted text if applicable
    semantic_description: Optional[str]     # natural language description of non-text content
    ocr_text: Optional[str]                  # text visible in image/screenshot
    document_summary: Optional[DocumentSummary]
    location_description: Optional[str]     # semantic description of location
    emotional_register_hint: Optional[str]  # brief inference about emotional context of media
    modality_flags: list[str]               # e.g. ["face_present", "screenshot", "new_location"]
    raw_voice_available: bool               # True only during SC-4; always False in final packet
    language_detected: Optional[str]        # ISO 639-1 code
    language_switch_detected: bool
```

---

## 6. Sub-Component 4 — Voice Prosody Extractor

### 6.1 Purpose

Spoken language carries emotional signal that text transcription discards. Hesitation, pitch elevation, vocal tremor, speaking pace, and volume dynamics are cues humans read automatically. When Nova operates in a voice input mode (not WhatsApp text — voice notes or a dedicated voice interface), these features form a free, high-value emotional signal channel.

**Scope:** This sub-component is **active only when a voice note or voice input is received.** It does not run on text messages. It runs in parallel with SC-3's transcription, using the same raw audio buffer that is discarded after both complete.

### 6.2 Feature Extraction Pipeline

Audio input → on-device processing only (no audio leaves the device).

**Recommended model stack:**

- **Primary:** SpeechBrain's emotion recognition (on-device, runs on CPU in < 3s for clips under 60s)
- **Fallback:** Rule-based prosody feature extraction (pitch variance, energy envelope, speech rate) using `librosa` — computationally trivial, no model required

**Extracted features:**

```python
class ProsodyFeatures:
    speech_rate_words_per_min: float         # baseline: 120–150 for casual speech
    speech_rate_deviation: float             # deviation from user's calibrated baseline
    pitch_mean_hz: float                     # fundamental frequency average
    pitch_variance: float                    # high variance → emotional/emphatic speech
    energy_mean_db: float                    # volume level
    energy_variance: float                   # fluctuation → dynamic, emotionally variable delivery
    pause_frequency: float                   # pauses per 100 words
    pause_mean_duration_ms: float            # average pause length
    voice_tremor_detected: bool              # micro-jitter in pitch — anxiety/distress marker
    vocal_fry_detected: bool                 # creaky voice — fatigue/low arousal marker
    breathiness_score: float                 # 0–1; breathiness often correlates with sadness/vulnerability
```

**Derived prosodic emotion estimate:**

```python
class ProsodyEmotionEstimate:
    valence: float          # –1 (negative) to +1 (positive)
    arousal: float          # 0 (calm) to 1 (activated)
    confidence: float       # 0–1; lower for noisy audio
    dominant_signal: Optional[Literal[
        "anxious",          # high pitch variance + fast rate + tremor
        "distressed",       # low energy + tremor + breathiness
        "flat_affect",      # low variance across all features; minimal expressiveness
        "animated",         # high energy + high variance + fast rate
        "fatigued",         # slow rate + vocal fry + low energy
        "neutral"
    ]]
```

The `ProsodyEmotionEstimate` is passed directly to Layer 3 (Emotion Classifier) as a **pre-textual emotional prior**. If the transcript says *"I'm fine"* but prosody signals distress (tremor, low energy, high breathiness), Layer 3 weights the prosodic signal meaningfully against the text-only assessment.

### 6.3 Calibration

Prosody interpretation is meaningless without user-specific calibration. The feature values above are absolute — but what constitutes "high pitch variance" for one user may be their baseline excited register.

After 5+ voice inputs from the same user, the system maintains a `VoiceCalibrationProfile`:

```python
class VoiceCalibrationProfile:
    baseline_speech_rate: float
    baseline_pitch_mean: float
    baseline_pitch_variance: float
    baseline_energy_mean: float
    samples_used: int                  # increases confidence in baseline
    calibration_confidence: float      # 0–1; <0.5 until 10+ samples
```

All prosody feature interpretations use **deviation from calibrated baseline** once `calibration_confidence > 0.5`. Before calibration, population-level norms are used with lower confidence weighting downstream.

### 6.4 Privacy Constraint

Raw audio is **never persisted to disk.** It exists only in RAM during the SC-3/SC-4 pass (< 5 seconds total processing time) and is explicitly freed after prosody extraction completes. What persists is only the `ProsodyFeatures` struct and `ProsodyEmotionEstimate` — structured data with no biometric reconstruction capability.

---

## 7. Sub-Component 5 — Input Perception Assembler

### 7.1 Purpose

The Assembler is not a processor — it is a **collector and validator**. It gathers the outputs from SC-1 through SC-4, validates completeness and consistency, resolves any conflicts between signals, and emits the single `InputPerceptionPacket` that all downstream layers consume.

### 7.2 Conflict Resolution Rules

When signals from different sub-components are in tension, the following resolution rules apply:

| Conflict | Resolution |
|---|---|
| Circadian prior says `low_vulnerability` (morning) but implicit signals show very high emotional intensity | Implicit signal score overrides the circadian prior; use `max(circadian_prior, implicit_emotional_intensity * 0.8)` |
| Text content is neutral but prosody signals distress | Set a `signal_mismatch: True` flag; Layer 3 uses this to apply the "stated vs. felt" logic |
| Voice note transcript is very short (< 10 words) but prosody features are expressive | Flag as `high_prosody_low_text`; the prosody signal carries more interpretive weight |
| Multiple modalities present (text + image) | `primary_modality = "mixed"`; both are included; text is prioritized for semantic content, image for emotional context |

### 7.3 Complete Output Schema — InputPerceptionPacket

This is the formal contract Layer 1 hands to every downstream layer. No field is optional in a completed assembly — all fields have explicit defaults if the relevant sub-component did not fire.

```python
class InputPerceptionPacket:

    # ── Identity & Timing ─────────────────────────────────────────────────────
    user_id: UUID
    message_id: UUID
    received_at: datetime                    # absolute UTC timestamp
    user_local_time: time                    # local time at user's timezone
    circadian_band: str                      # one of 6 bands
    circadian_mood_prior: float              # 0–1; estimated vulnerability prior
    day_of_week: str                         # "Monday"–"Sunday"
    is_weekend: bool

    # ── Session Gap ───────────────────────────────────────────────────────────
    session_gap_seconds: int                 # raw gap since last message
    gap_category: str                        # one of 7 buckets
    human_readable_gap_label: str            # "a few days ago", etc.
    is_new_session: bool                     # True if gap > 30 minutes

    # ── Temporal Anomaly ──────────────────────────────────────────────────────
    anomaly_detected: bool
    context_note: Optional[str]              # plain-language anomaly description

    # ── Relationship Temporal Context ─────────────────────────────────────────
    relationship_age_days: int
    total_sessions_with_user: int
    avg_session_frequency_days: float
    gap_vs_baseline_ratio: float             # current gap / average gap; > 1 = longer than usual

    # ── Pending Threads ───────────────────────────────────────────────────────
    due_threads: list[NarrativeThread]       # max 2, sorted by priority
    overdue_thread_count: int                # threads past due not returned (context for Layer 6)

    # ── Fuzzy Label Helper ────────────────────────────────────────────────────
    # Used by Layer 2 Memory Arbiter; the resolver provides a utility function
    # rather than pre-computing labels for every memory here.
    fuzzy_label_for_timestamp: Callable[[datetime], str]

    # ── Implicit Signals ──────────────────────────────────────────────────────
    response_latency_ms: Optional[int]       # None if no prior Nova message this session
    latency_signal: Optional[str]            # "reactive", "quick", "considered", etc.
    latency_deviation_from_baseline: Optional[float]  # ratio vs. user's median
    deletion_occurred: bool
    deletion_count: int
    final_length_vs_peak_ratio: Optional[float]
    message_length_chars: int
    length_ratio_vs_baseline: float
    initiation_type: str                     # "user_initiated_cold", "continuation", etc.
    is_message_burst: bool
    burst_count: int                         # 1 if not a burst
    implicit_emotional_intensity_score: float  # 0–1 aggregate

    # ── Modality ──────────────────────────────────────────────────────────────
    primary_modality: str
    raw_text: Optional[str]                  # original text content
    modality_context: ModalityContext        # full multimodal normalization output

    # ── Prosody (voice only) ──────────────────────────────────────────────────
    prosody_features: Optional[ProsodyFeatures]
    prosody_emotion_estimate: Optional[ProsodyEmotionEstimate]
    signal_mismatch: bool                    # True if text vs. prosody/implicit signals conflict

    # ── Composite Pre-Linguistic Emotional Prior ──────────────────────────────
    # Final pre-linguistic estimate for Layer 3 before it reads message content.
    # Weighted combination of circadian_mood_prior, implicit_emotional_intensity,
    # and prosody_emotion_estimate (if present).
    composite_emotional_prior: float         # 0–1; Layer 3 uses as Bayesian prior
    prior_confidence: float                  # 0–1; higher when more signals contributed
```

### 7.4 The Composite Emotional Prior

This is the single most important computed value in Layer 1. It synthesizes all pre-linguistic signals into one float that Layer 3 uses as its Bayesian prior before reading the message content.

```python
def compute_composite_prior(
    circadian_mood_prior: float,
    implicit_intensity: float,
    prosody_estimate: Optional[ProsodyEmotionEstimate],
    anomaly_detected: bool
) -> tuple[float, float]:

    signals = []
    weights = []

    # Circadian prior: lowest weight (population-level baseline)
    signals.append(circadian_mood_prior)
    weights.append(0.15)

    # Implicit signals: moderate weight (behavioral, user-specific)
    signals.append(implicit_intensity)
    weights.append(0.35)

    # Prosody: highest weight when present (direct emotional channel)
    if prosody_estimate and prosody_estimate.confidence > 0.4:
        prosody_neg = max(0.0, -prosody_estimate.valence)  # map negative valence to vulnerability
        signals.append(prosody_neg)
        weights.append(0.50)

    # Anomaly bonus: atypical timing increases prior slightly
    if anomaly_detected:
        signals = [s + 0.08 for s in signals]

    # Normalize and compute weighted average
    total_weight = sum(weights)
    prior = sum(s * w for s, w in zip(signals, weights)) / total_weight
    confidence = min(len(signals) / 3.0, 1.0)

    return min(prior, 1.0), confidence
```

A `prior_confidence < 0.4` means only one signal was available (typically circadian only — new user with no voice input). Layer 3 should treat a low-confidence prior as a weak suggestion, not a strong signal.

---

## 8. Data Storage and Persistence

Layer 1 is **stateless in execution** but requires access to per-user state that persists between sessions. The following databases are read and written:

| Data | Store | Access Pattern | Location |
|---|---|---|---|
| `UserTemporalProfile` | SQLite (user_meta.db) | Read every message, write after session end | On-device |
| `NarrativeThread` records | SQLite (threads.db) | Read at session start, write via State Updater (Layer 2) | On-device |
| `VoiceCalibrationProfile` | SQLite (user_meta.db) | Read on voice input, write after each voice session | On-device |
| Per-user message latency history | SQLite (user_meta.db) | Read every text message, append after each message | On-device |
| Per-user message length history | SQLite (user_meta.db) | Read every message, append after each message | On-device |

**Write timing:** All state updates (updating `UserTemporalProfile`, appending latency/length history) happen **after** the `InputPerceptionPacket` is emitted. Layer 1 reads the state it needs, fires the packet, then the State Updater (end of pipeline, Layer 2's responsibility) handles persistence. Layer 1 never blocks on a write.

---

## 9. Downstream Consumption Contract

Every downstream layer consumes specific fields from the `InputPerceptionPacket`. This table is the formal contract.

| Layer | Fields Consumed | Purpose |
|---|---|---|
| **Layer 2** (Memory) | `received_at`, `fuzzy_label_for_timestamp`, `gap_category`, `due_threads`, `user_id` | Attach correct temporal labels to retrieved memories; surface due thread context |
| **Layer 3** (Emotion) | `composite_emotional_prior`, `prior_confidence`, `signal_mismatch`, `prosody_emotion_estimate`, `circadian_band`, `implicit_emotional_intensity_score` | Bayesian prior before content analysis; mismatch flag triggers stated-vs-felt logic |
| **Layer 4** (Persona) | `circadian_band`, `gap_category`, `relationship_age_days`, `is_new_session`, `context_note` | Adjust tone, verbosity, re-entry posture, formality |
| **Layer 5** (Social) | `due_threads`, `initiation_type` | Thread-based social coaching triggers; session initiation context |
| **Layer 6** (Proactivity) | `due_threads`, `overdue_thread_count`, `gap_category`, `anomaly_detected`, `initiation_type`, `gap_vs_baseline_ratio` | Check-in trigger evaluation; intrusion cost input |
| **Layer 7** (Goals) | `circadian_band`, `anomaly_detected`, `gap_vs_baseline_ratio` | Life event signal detection; temporal context for goal-related inference |
| **Layer 9** (Output/Interaction Orchestrator) | `circadian_band`, `implicit_emotional_intensity_score`, `is_message_burst`, `latency_signal` | Tune typing simulation speed and thinking pauses; burst → holistic reading |
| **Layer 13** (Cold Start) | `relationship_age_days`, `total_sessions_with_user`, `is_new_session`, `initiation_type` | Cold start graduation criteria check; first-session detection |

**Fields never passed to the LLM directly:**
- Raw timestamps in ISO format
- `circadian_mood_prior` as a float
- `composite_emotional_prior` as a float
- Any prosody feature value as a raw number

These values are consumed by orchestration logic and translated into natural-language prompt modifiers. The LLM receives behavioral instructions (e.g., *"User appears emotionally elevated — validate before any task content"*), not raw signal values.

---

## 10. Execution Performance Targets

| Path | Target Latency | Notes |
|---|---|---|
| Text-only message, returning user | < 5ms | All computations are lookup + arithmetic |
| Text-only message, new user | < 5ms | Same; no calibration baseline slows it |
| Text + image | < 1500ms | LLaVA inference dominates; runs in parallel with SC-1/SC-2 |
| Voice note (< 60s) | < 3000ms | Whisper.cpp + SpeechBrain on-device |
| Voice note (> 60s) | < 5000ms | Linear scaling with audio length |

SC-1 and SC-2 always run synchronously and complete in microseconds. SC-3 and SC-4 run asynchronously and rejoin before the Assembler emits the packet. The Assembler will not emit until all relevant sub-components complete — total latency is dominated by the slowest active sub-component.

---

## 11. Error Handling and Fallback Behavior

Layer 1 must never fail silently or block the conversation pipeline. All error cases have defined fallback behaviors:

| Failure Case | Fallback Behavior |
|---|---|
| Timezone unknown (new user, no explicit set) | Default to UTC; flag `timezone_confidence: low`; infer from message timestamps over first 3 sessions |
| Thread database read failure | Return `due_threads = []`; log error; conversation proceeds without thread surfacing |
| Voice note too noisy for transcription (Whisper confidence < 0.5) | Return transcript with low-confidence flag; SC-4 skipped; modality falls back to `voice_untranscribed` with note |
| Image normalizer failure (corrupt file, unsupported format) | Return `ModalityContext` with `primary_modality = "image_unprocessed"` and semantic description `"[Image could not be processed]"`; conversation proceeds |
| Latency data missing (no prior Nova message this session) | `response_latency_ms = None`, `latency_signal = None`; implicit intensity score computed from remaining signals |
| User temporal profile not found (database miss) | Initialize with population defaults; flag `cold_start_profile: True`; no anomaly detection until 5 sessions of data |

**Hard rule:** The `InputPerceptionPacket` is always emitted, even if several sub-components failed. Missing fields are `None` or default values with explicit flags. A partial packet is always better than no packet — the downstream pipeline can tolerate missing optional signals; it cannot tolerate a missing packet.

---

## 12. Implementation Specification

### 12.1 Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| SC-1 (Temporal Resolver) | Pure Python / Kotlin (depending on platform) | Zero-dependency, deterministic, testable |
| SC-2 (Implicit Signals) | Pure Python / Kotlin | Arithmetic only; no model |
| SC-3 — Image | LLaVA-1.6 7B (local, GGUF via llama.cpp) or GPT-4o Vision API (opt-in cloud) | Local-first; cloud opt-in for accuracy |
| SC-3 — Voice transcript | Whisper.cpp (small model, on-device) | Fast, accurate, no network needed |
| SC-3 — Document | Apache Tika (text extraction) | Industry standard; handles 1000+ formats |
| SC-4 (Prosody) | SpeechBrain ECAPA-TDNN emotion model + librosa | Compact, on-device capable |
| Assembler | Pure Python data class construction | Deterministic composition |
| State storage | SQLite + SQLCipher (encrypted at rest) | On-device, zero-configuration, encrypted |

### 12.2 Service Interface

Layer 1 exposes a single synchronous function to the Conversation Orchestrator:

```python
async def process_input_event(
    user_id: UUID,
    raw_message: str,
    received_at: datetime,
    attachments: list[AttachmentPayload],        # images, voice notes, files
    client_metadata: ClientMetadata             # latency, deletion events, burst info
) -> InputPerceptionPacket:
    ...
```

`ClientMetadata` is a structured payload the client app sends alongside every message:

```python
class ClientMetadata:
    nova_last_delivered_at: Optional[datetime]   # when Nova's last message rendered
    user_typing_started_at: Optional[datetime]   # when user began typing this message
    deletion_occurred: bool
    deletion_count: int
    peak_draft_length_chars: int
    final_draft_length_chars: int
    is_burst: bool
    burst_count: int
    burst_messages: Optional[list[str]]          # all messages in burst if applicable
    session_id: UUID
```

The client is responsible for measuring and reporting `ClientMetadata`. The server cannot derive message latency or deletion behavior post-hoc — these must be sent from the client at message time.

### 12.3 Testing Requirements

| Test Category | Coverage Target | Method |
|---|---|---|
| Circadian band mapping | 100% of 24-hour range | Unit tests with synthetic timestamps |
| Gap classification accuracy | 100% of 7 buckets | Unit tests across boundary conditions |
| Anomaly detection | True positive rate > 85% | Against labeled synthetic dataset |
| Thread surfacing priority | Correct priority ordering | Unit tests with synthetic thread sets |
| Fuzzy label correctness | Human evaluation of 200 random labels | Naturalness rating by 3 reviewers |
| Implicit intensity score | Calibration test against self-reported emotional states | Correlation study with 50+ session logs |
| Multimodal normalization | Image: 100 test images across all type categories | Automated + human review |
| Assembly completeness | 100% of fields populated or explicitly None | Schema validation tests |
| Fallback behavior | All error cases explicitly tested | Unit tests per error case |

---

## 13. Relationship to Adjacent Layers

**Upstream (nothing):** Layer 1 is the entry point. There is no Layer 0 in the current architecture, though a future Layer 0 (ambient sensing — always-on audio, screen state detection) would feed additional signals into SC-4 and SC-2 before the pipeline begins.

**Downstream (all other layers):** Layer 1 hands a packet to all other layers. It never receives data back from downstream layers during processing — it is a pure source, not a consumer.

**State Updater (Layer 2 responsibility):** After the full pipeline completes (Layers 1 through response generation), the State Updater writes back to Layer 1's state:
- Updates `UserTemporalProfile` with the new session data
- Appends latency and length history
- Creates or resolves `NarrativeThread` records based on conversation content
- Layer 1 trusts the State Updater to maintain its state; it does not write state itself

---

## 14. Design Principles Summary

These principles are constraints that must be honored in every implementation decision within Layer 1:

1. **Deterministic above all else.** Layer 1 contains zero LLM calls in its core path (SC-1, SC-2, Assembler). The only model calls are in SC-3 and SC-4, triggered only by non-text input. A deterministic Layer 1 is auditable, testable, and will never hallucinate temporal context.

2. **Signals, not conclusions.** Layer 1 outputs signals and priors. It does not conclude *"user is in crisis"* or *"user is happy."* It outputs *"composite emotional prior: 0.72, anomaly detected, late-night band, high implicit intensity."* Layer 3 draws conclusions. Layer 1 only measures.

3. **Fuzzy human language, always.** Absolute timestamps never reach the LLM. The `fuzzy_label_for_timestamp` utility is the only path by which temporal information enters the response generation pipeline.

4. **Privacy by design.** Raw audio is never persisted. Face recognition is disabled. Deleted text content is never captured — only the behavioral metadata of its deletion. Client metadata (latency, deletion counts) is treated with the same encryption as message content in transit and storage.

5. **Fail gracefully, always emit.** Layer 1 never blocks the conversation pipeline. A partial packet with explicit `None` values is always preferable to a missing packet.

6. **The asymmetry fix.** Layer 9 generates implicit signals (typing simulation, deletion, backchannels) as output. Layer 1 reads equivalent signals as input. The system is now symmetrical: Nova performs what it also reads.

---

*This document specifies Layer 1 completely. No behavior of Layer 1 should require assumptions or inferences from other documents. All schemas, algorithms, data stores, error cases, and downstream contracts are defined above.*
