# Frontend Follow-Up: Populating Layer 1's Real Implicit-Signal Fields

Backend follow-up (2026-08-09) made Layer 1 SC-2's implicit-signal plumbing real end-to-end:
`api/schemas.py::ChatRequest` now carries additive client-behavioral fields, and
`api/assembly.py::perceive` forwards them into a real `ClientMetadata` object consumed by
`backend/layer1_input/implicit_signals.py`. See `docs/layer-1-architecture.md` §18 for the backend
side. **No frontend client sends non-default values for any of these fields yet** — this doc is
the scoped, standalone spec for whoever picks up that half. Not built this pass (explicit scope
decision, 2026-08-09).

One field — `response_latency_ms` — is **already real without any frontend change** (Layer 1 now
derives it server-side from `Session.last_delivered_at`). Everything below needs client
instrumentation.

## What to send

`POST /chat` and `POST /chat/stream` (`frontend/lib/api/client.ts`, `sendMessage`/`streamMessage`
around line 222) currently send only `{ message, session_id }`
(`frontend/lib/api/types.ts` `ChatRequest`-equivalent type). Extend the request body with:

| Field | Type | Source |
|---|---|---|
| `user_typing_started_at` | ISO datetime string | Timestamp of the first keystroke in the current draft (reset once the draft is sent or cleared). |
| `deletion_occurred` | bool | Whether the user deleted/backspaced a meaningful chunk of the draft before sending. |
| `deletion_count` | int | Number of distinct deletion events (backspace bursts, not per-keystroke) during composition. |
| `peak_draft_length_chars` | int | The longest the draft ever got before the final send. |
| `final_draft_length_chars` | int | The draft's length at send time (compare to peak for a "wrote a lot, cut it down" signal). |
| `is_burst` | bool | Whether this message was sent as part of a rapid multi-message burst (see below). |
| `burst_count` | int | How many messages are in the current burst, including this one. |
| `is_reply_to_proactive` | bool | Whether this message was sent in direct response to a Nova-initiated (proactive) message. |

## Where to instrument (`frontend/components/chat/Composer.tsx`)

`Composer` currently only tracks `value`/`onChange`/`onSend` (67 lines, no behavioral state). It
needs to become the owner of a small per-draft tracking object, reset on every send:

```ts
// sketch — not the real implementation
const draftStartedAt = useRef<Date | null>(null);
const peakLength = useRef(0);
const deletionCount = useRef(0);

// on first keystroke of a fresh (empty -> non-empty) draft: draftStartedAt.current = new Date()
// on every onChange: peakLength.current = Math.max(peakLength.current, value.length)
// on a backspace/delete that shrinks the value by more than ~3 chars in one edit: deletionCount.current += 1
// on send: pass {user_typing_started_at: draftStartedAt.current, deletion_occurred: deletionCount.current > 0,
//   deletion_count: deletionCount.current, peak_draft_length_chars: peakLength.current,
//   final_draft_length_chars: value.length}, then reset all three refs to their initial state.
```

**Burst detection** (`is_burst`/`burst_count`) is cross-message state, not per-draft — it belongs a
level up, in whatever owns the message list (`frontend/lib/hooks/useChatStream.ts` or
`frontend/app/chat/page.tsx`), tracking "how many user messages have been sent since Nova's last
reply arrived." Reset the counter to 1 the moment a Nova message is received; increment it on each
user send before Nova has replied again. `is_burst = burst_count > 1`.

**`is_reply_to_proactive`**: Layer 6 now has a real push delivery channel (`GET /proactive/stream`
SSE + `frontend/app/proactive/page.tsx`, 2026-08-09 — see `docs/layer-6-architecture.md`'s Live
Wiring Status). `ChatRequest.is_reply_to_proactive` and `make_proactive_response_writer`
(`api/state.py`) are already wired server-side to close the SC-5 response-tracking loop; what's
still missing is the frontend actually setting this field true when the user replies to a
delivered proactive item (e.g. from the `/proactive` page) rather than a normal chat turn. Until
that wiring lands it should be sent as `false` (the current default), not fabricated.

## Wiring into the API client

`frontend/lib/api/client.ts`'s `jsonPost` calls (around line 222 for `sendMessage`, and the
streaming equivalent) need the new fields merged into the request body object. `types.ts`'s
`ChatRequest`-equivalent interface needs the matching optional fields, mirroring
`api/schemas.py::ChatRequest` field-for-field so a future backend field never silently gets
dropped by a stale frontend type.

## What this unlocks once shipped

- Layer 1 SC-2's `implicit_emotional_intensity_score` moves for real on every signal, not just
  latency (already live server-side).
- Layer 3's `composite_prior` gate (`docs/layer-3-architecture.md`, `integrate_prior`'s `> 0.6`
  check) is **still not reachable from the latency signal alone** — hand-computed the composite-
  prior formula (`backend/layer1_input/assembler.py::compute_composite_prior`): even at the
  highest circadian band (`early_morning`, 0.80) plus the maximum possible latency-only intensity
  contribution (0.25, `intensity_latency_scale`) plus the anomaly bonus, the prior tops out around
  ~0.50, below the `> 0.6` gate. Closing this gate for real needs the deletion/burst signals this
  doc specifies, not just the latency signal the backend pass already wired.
- `docs/layer-9-architecture.md`'s `voice_mode` forwarding gap (currently blocked on this same
  `ChatRequest` gap) — once attachment/modality fields exist here too (out of scope of this doc;
  see the multimodal note below).

## Explicitly out of scope here (separate infra project)

SC-3 (multimodal normalization) and SC-4 (voice prosody) need real backend implementations —
image description, speech-to-text, document extraction — none of which exist anywhere in this
codebase (`backend/layer1_input/multimodal_normalizer.py`'s `ImageBackend`/`VoiceBackend`/
`DocumentBackend` are injectable Protocols with zero concrete implementations, and nothing in
`api/assembly.py` registers one). Sending attachment bytes from the frontend without a backend to
process them would be pure plumbing with no effect — not attempted here. This is a genuinely
separate, larger project (build the backends first, then wire the frontend upload path), tracked
in `docs/POLISH_BACKLOG.md`'s Layer 1 entry, not this doc.
