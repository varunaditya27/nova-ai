# Nova AI — API Reference

Complete reference for the Nova AI HTTP backend: every endpoint, its request/response schema, and
the conventions a frontend needs. Generated from the live FastAPI app (`api/main.py`); the
machine-readable schema is always available at **`GET /openapi.json`** and an interactive explorer at
**`GET /docs`** (Swagger UI) / **`GET /redoc`**.

- **Base URL (local):** `http://127.0.0.1:8000`
- **Content type:** `application/json` for all request/response bodies except `POST /chat/stream`
  (`text/event-stream`) and `POST /voice` (`audio/mpeg`).
- **Auth:** none yet — single-user. The active user is `config.system.default_user_id`
  (env `NOVA_USER_ID`, default `local-user`). Auth/multi-user is a deliberate follow-up.
- **CORS:** allowed origins come from `config.api.cors_origins` (`config/defaults.yaml`, overridable
  via `config/local.yaml`). Add your frontend origin there (e.g. `http://localhost:5173`).
- **Errors:** uniform FastAPI shape `{"detail": "<message>"}`. Codes used: `404` (not found),
  `422` (request validation), `503` (a backend dependency — DB/model/TTS — is unavailable),
  `500` (unexpected job failure). `POST /chat` degrades internally and returns `503` only if the
  whole turn throws.

---

## Conventions

- **Timestamps** in responses are ISO-8601 strings (or `null`). The LLM itself never sees raw
  timestamps (Layer-1 fuzzy labels), but the API surfaces real ISO times for the UI.
- **No raw scores reach the model**, but the API *does* expose numeric fields (recall importance,
  relationship calibration, priorities) for the UI to render.
- **Single `ToolManager` + `voice_backend` + orchestrator** live on the app for the process, so a
  tool confirmation issued during a `/chat` turn is confirmable later via `/tools/confirm`.

---

## Health

### `GET /health`
Liveness. Always `200`.
```json
{ "status": "ok" }
```

### `GET /health/ready`
Readiness — probes Postgres. `200` when reachable, `503` otherwise (never leaks DB detail).
```json
{ "status": "ready" }                          // 200
{ "status": "not_ready", "component": "postgres" }  // 503
```

---

## Conversation

### `POST /chat`
Drive one full conversation turn (all 13 layers: crisis veto → recall → classify → cold-start
overlay → tool use → generate → SC-1 guardrails → Layer-9 delivery → post-turn writes).

**Request — `ChatRequest`**
| field | type | required | notes |
|---|---|---|---|
| `message` | string | yes | the user's message |
| `session_id` | string \| null | no | omitted → a new UUID is minted and returned |

**Response — `ChatResponse`**
| field | type | notes |
|---|---|---|
| `response` | string | the delivered, guardrailed text |
| `conversation_mode` | string | `casual` \| `emotional_support` \| `crisis` \| `celebration` \| `technical_discussion` \| `goal_planning` \| `social_coaching` \| `life_review` |
| `cognitive_system` | string | `system1` (fast, local) or `system2` (deep) |
| `crisis_active` | bool | true when Layer-11 replaced the response |
| `crisis_tier` | string \| null | `tier_1` \| `tier_2` \| `tier_3` when crisis, else null |
| `refined` | bool | Agent 4b emotion-refinement ran |
| `tool_invoked` | bool | a Layer-8 tool handled the turn (see `/tools/*`) |
| `confabulation_guard` | bool | true when no memories were recalled (model told not to invent) |
| `echoes` | list | memories Nova recalled this turn: `{summary, when, created_at}` — render as tiny dismissible "echoes" |
| `session_id` | string | echo (or minted) session id |

`curl -X POST /chat -d '{"message":"hey Nova","session_id":"s1"}'`

### `POST /chat/stream`
The **same full turn**, streamed as Server-Sent Events. Not token-from-LLM: the whole turn (crisis
veto + guardrails + post-turn writes) runs first, then the delivered text is replayed as
overlay-paced token frames — so SC-1 always runs before delivery. Response header `X-Session-Id`
carries the session id. Media type `text/event-stream`.

**Frame sequence:** one `meta`, then zero-or-more `thinking_pause`/`backchannel`, then N `token`,
then one `done`. On failure a terminal `error`. The `thinking_pause`/`backchannel` frames (added
2026-08-09) replay Layer 9's real pre-response event sequence — additive only, a client that
doesn't recognize them can ignore them and the `meta`/`token`/`done` contract is unchanged.
```
event: meta
data: {"session_id":"s1","conversation_mode":"casual","cognitive_system":"system1",
       "crisis_active":false,"refined":false,"confabulation_guard":false}

event: thinking_pause
data: {"duration_ms":1025}                    // optional, before typing starts

event: backchannel
data: {"text":"Oh no...","delay_ms":600}      // optional, a brief acknowledgment bubble

event: token
data: {"token":"Hey ","delay_ms":40}          // concatenating all tokens == response text

event: done
data: {"session_id":"s1","conversation_mode":"casual","cognitive_system":"system1",
       "crisis_active":false,"refined":false}

event: error
data: {"session_id":"s1","message":"stream interrupted; please retry"}   // only on failure
```

### `POST /voice`
Synthesize a text response to speech (Layer-9 SSML → Kokoro TTS). Returns raw audio
(`audio/mpeg`), or `503` if TTS is unavailable/failed (fall back to text).

**Request — `VoiceRequest`**
| field | type | required | notes |
|---|---|---|---|
| `text` | string | yes | text to speak |
| `conversation_mode` | string | no | the mode `/chat` returned; mapped to a Layer-9 prosody profile. Default `casual` |
| `voice_id` | string \| null | no | Kokoro voice (`af_sky`, `af_bella`, `am_adam`, …); default from config |

Response body: binary MP3. `curl -X POST /voice -d '{"text":"hello"}' --output out.mp3`

### `POST /voice/transcribe` → `TranscribeOut`
Multipart audio upload (`file`), transcribed by the local faster-whisper STT backend (fully
offline). Returns `{transcript, confidence, language}`. `503` if the STT backend is unavailable or
transcription fails — the client should fall back to letting the user type.

---

## Conversation log + annotations

The single permanent thread. Every turn (user + Nova) is persisted; the UI loads history here rather
than replaying `/chat`. Navigate by search / jump / continue-from-bottom, never long scrolling.

### `GET /messages?limit=50&before=<cursor>` → `[MessageOut]`
Newest-first page (max `limit` 200). To page **back** (older), pass the last item's `cursor` as
`before`; a page shorter than `limit` means you've reached the start. Each item:
| field | type | notes |
|---|---|---|
| `message_id` | string | annotate via the endpoints below |
| `cursor` | int | monotonic row id; pass the last item's value as `before=` to page back |
| `role` | string | `user` \| `nova` |
| `content` | string | |
| `created_at` | iso \| null | |
| `conversation_mode` | string \| null | on Nova turns |
| `crisis_active` / `tool_invoked` | bool | on Nova turns |
| `echoes` | list | `{summary, when, created_at}` recalled that turn |
| `bookmarked` / `bookmark_category` | bool / string | |
| `is_milestone` / `milestone_label` | bool / string | |

### `GET /messages/search?q=&start=&end=&limit=` → `[MessageOut]`
Deterministic **keyword + date-range** search (`start`/`end` are ISO datetimes). Predictable, no AI.

### `GET /memory/search?q=&limit=5` → `[MemoryOut]`
Semantic **"AI" search** over episodic memory ("the time I was scared") — embeds the query and returns
nearest episodes; degrades to a keyword scan when the vector index is cold. Distinct from keyword search.

### Bookmarks
- `POST /messages/{id}/bookmark` `{ "category"?: string }` → `MessageOut` (`404` if unknown)
- `DELETE /messages/{id}/bookmark` → `MessageOut`
- `GET /bookmarks?category=` → `[MessageOut]`

### Milestones
- `POST /messages/{id}/milestone` `{ "label"?: string }` → `MessageOut`
- `DELETE /messages/{id}/milestone` → `MessageOut`
- `GET /milestones` → `[MessageOut]` (oldest-first — a life album)

---

## Continuity — Digital Desk / calendar / museum

Lenses derived over data other layers already produce; the chat is never touched.

### `GET /home` → `HomeOut`
The authenticated landing ("Digital Desk").
```
{ "greeting": "Good evening", "current_chapter": <latest longitudinal theme|null>,
  "relationship_stage": "acquaintance", "last_interaction_at": <iso|null>,
  "weather": "sunny|clear|cloudy|distant",  "active_goals": 4,
  "top_proactive": <the thought Nova is holding|null>, "cold_start_active": false,
  "message_count": 128 }
```

### `GET /calendar?start=&end=` → `CalendarOut`
Per-day message counts for a heatmap (defaults to the current month).
```
{ "start": iso, "end": iso, "days": { "2026-07-07": 12, "2026-07-08": 3 } }
```

### `GET /museum` → `MuseumOut`
"Firsts" derived from the log + milestones + goals.
```
{ "entries": [ { "label": "First conversation", "content": "...", "when": iso }, … ] }
```

---

## Goals (Layer 7)

### `GET /goals?status=<status>`
Active goals by default; pass `status` to filter (`tentative`|`active`|`on_track`|`at_risk`|…).
Returns `[GoalOut]`.

### `GET /goals/{goal_id}` → `GoalOut` (`404` if absent)

### `POST /goals` → `GoalOut` (`201`)
**Request — `GoalCreate`:** `{ "title": string, "description": string? }`

### `PATCH /goals/{goal_id}` → `GoalOut` (`404` if absent)
Update a goal's `status` and/or `progress_score`. **Request — `GoalUpdate`:**
`{ "status": string?, "progress_score": float? }`. `progress_score` is clamped to `[0,1]`; an
invalid `status` (not a `GoalStatus`) is `422`.

### `DELETE /goals/{goal_id}` → `204` (`404` if absent)
Permanently removes the goal row (user-scoped).

**`GoalOut`**
| field | type |
|---|---|
| `goal_id` | string |
| `title` | string |
| `status` | string |
| `progress_score` | float |
| `description` | string |

> Goals are also **extracted automatically** from `/chat` messages (Layer-7 pipeline). A goal with an
> upcoming `deadline`/milestone seeds a proactive check-in (see `/proactive`).

---

## Memory (Layer 2) + Privacy (Layer 12)

### `GET /memory/audit` → `MemoryAuditOut`
```
{ "episodic": [MemoryOut], "semantic": [SemanticOut] }
```
- **`MemoryOut`**: `memory_id, summary, importance (float), created_at (iso|null), topic_tags[]`
- **`SemanticOut`**: `memory_id, statement, confidence (float)`

### `GET /memory/{memory_id}` → `MemoryOut` (`404` if absent or deleted)

### `GET /memory/integrity` → `IntegrityOut`
Verifies all three tamper-evident hash chains (Layer 2 memory audit, Layer 11 safety record,
Layer 12 privacy audit).
```
{ "status": "INTACT" | "TAMPER_DETECTED", "audit_chain_ok": bool, "privacy_chain_ok": bool,
  "safety_chain_ok": bool }
```

### `DELETE /memory/{memory_id}` → `MemoryDeletionOut`
Real Layer-12 selective deletion — a genuine "forget" (content/embedding zeroed, unrecallable; row
retained for proof), a signed certificate, and a privacy-audit chain entry. Cascade-affected
semantic facts and weekly summaries are genuinely redacted in place (references stripped; a fact
left with zero support is deprecated), not just reported. `404` if already gone.
```
{ "deleted": int, "memory_id": string, "certificate": string, "cascade": string }
```

### `GET /memory/audit/full` → `MemoryAuditViewOut`
Layer-12 SC-3's richer transparency view — human-readable importance labels, semantic facts,
identity beliefs, and crisis/goal counts. Distinct from `GET /memory/audit` above.
```
{ "user_id": string, "generated_at": iso, "total_memory_count": int,
  "episodic": [AuditableMemoryOut], "semantic": [AuditableFactOut], "identity": [AuditableFactOut],
  "crisis_session_count": int, "active_goal_count": int }
```
- **`AuditableMemoryOut`**: `memory_id, date_formed, human_readable_summary, importance_label
  ("Low"|"Medium"|"High"|"Anchored"), topic_tags[], emotion_at_formation, reinforcement_count`
- **`AuditableFactOut`**: `fact_id, fact_text, category, confidence (float), source_episode_ids[],
  is_user_confirmed (bool)`

### `GET /memory/audit/query?q=` → `AuditQueryResultOut`
Natural-language audit query — "what do you know about my job?" Returns matching record ids only;
fetch detail via `GET /memory/{id}`.
```
{ "query": string, "total_count": int, "intent_type": string, "memory_ids": [string] }
```

### `POST /memory/{memory_id}/correct` → `CorrectionResultOut`
Layer-12 SC-3 Memory Correction — accepted without debate. Body: `{ "correction_type":
"edit"|"downgrade"|"decontextualize"|"anchor"|"expire"|"confirm", "new_content"?, "new_importance"?,
"tags_to_remove"?, "expiry_date"? }`.
```
{ "success": bool, "memory_id": string, "correction_type": string, "detail": string }
```

---

## Safety (Layer 11)

### `GET /safety/events?limit=20` → `[SafetyEventOut]`
Recent crisis assessments (append-only log; `NONE` tier turns are not logged).
| field | type |
|---|---|
| `tier` | string (`tier_1`\|`tier_2`\|`tier_3`) |
| `confidence` | float |
| `detected_at` | iso \| null |
| `signal_types` | list |

---

## Relationship (Layer 4/5)

### `GET /relationship` → `RelationshipOut`
Per-user relationship state — stage progression **and** the learned communication-style calibration
(persona-param learning). Every `/chat` turn advances it.
| field | type | notes |
|---|---|---|
| `stage` | string | `new`→`acquaintance`→`developing`→`established`→`close` (by session count) |
| `total_sessions` | int | |
| `total_messages_exchanged` | int | |
| `tie_strength` | float | |
| `trust_score` | float | |
| `formality_preference` | float | 0=casual … 1=formal (learned) |
| `response_length_preference` | float | 0=terse … 1=verbose (learned) |
| `question_tolerance` | float | 0=dislikes being asked … 1=welcomes it (learned) |
| `unsolicited_advice_tolerance` | float | 0=don't advise … 1=open to suggestions (learned) |

---

## People (Layer 5)

Read-only view of Layer 5's persisted social graph — people Nova knows about, built exclusively
from what the user has stated, never inferred.

### `GET /people` → `PersonOut[]`
Every person in the graph, sorted by `mention_count` descending.
| field | type | notes |
|---|---|---|
| `person_id` | string | |
| `display_name` | string | |
| `relationship_type` | string | e.g. `close_friend`, `family_immediate`, `colleague` |
| `relationship_valence` | float | -1.0…1.0 |
| `valence_trend` | float | + improving, − worsening |
| `interaction_frequency` | string | |
| `is_support_source` | bool | |
| `active_conflict` | bool | |
| `mention_count` | int | |
| `last_mentioned` | string\|null | ISO datetime |

### `GET /people/{person_id}` → `PersonDetailOut`
`PersonOut` fields plus:
| field | type | notes |
|---|---|---|
| `recent_events` | `SocialEventOut[]` | that person's event timeline, newest first |
| `active_patterns` | `SocialPatternOut[]` | active `SocialPattern`s involving them |

`404` if the id doesn't exist.

---

## Onboarding (Layer 13)

### `GET /onboarding` → `OnboardingOut`
```
{ "cold_start_active": bool, "session_index": int }
```
While `cold_start_active`, Nova runs **active elicitation** — it weaves at most one onboarding
question per session into `/chat` replies when a natural topic arises (never front-loaded, never
repeated). It self-graduates at `config.onboarding.graduation_sessions` (default 5).

---

## Sessions

### `GET /sessions` → `[SessionOut]`
`{ "session_key": string, "turn_count": int }` per session.

---

## Proactivity (Layer 6)

### `GET /proactive?limit=5` → `[ProactiveItemOut]`
Top pending outreach candidates (highest priority first), gated server-side through the real SC-3
Timing & Delivery Gate — an item only appears here once it genuinely clears every block group
(crisis aftermath, relationship-too-new, daily cap, min-gap, user preferences, content quality).
Populated per-turn from active goals with an upcoming deadline/milestone; maintained
(re-prioritized/expired/message-generated) by the `proactive_check` job. Empty while the user is
cold-starting.
| field | type |
|---|---|
| `item_id` | string |
| `item_type` | string (e.g. `goal_check_in`) |
| `status` | string (`pending`\|`deferred`) |
| `content_basis` | string (internal fragment, e.g. `"Goal: X \| Milestone: Y"`) |
| `message` | string (the real SC-4-generated delivery text; `""` until the background job has produced one) |
| `current_priority` | float |

### `GET /proactive/stream` → `text/event-stream`
SC-3/SC-4 push channel. Bounded-lifetime SSE connection (~25 min; the client's `EventSource`
auto-reconnects natively on close). Frames: `connected` (once), `heartbeat` (every ~30s),
`item` (`{item_id, item_type, message, current_priority}`) the moment a candidate is both
gate-passing and already has a real generated message — never pushes `content_basis`.

### `POST /proactive/{item_id}/delivered` → `{item_id, status}`
SC-5: call this the moment a client actually shows a proactive item to the user (e.g. right after
receiving it). Transitions the item to `sent` with a real `sent_at` timestamp, which the next
`/chat` turn's `is_reply_to_proactive: true` flag uses to attribute a reply and close the
response-tracking loop. `404` if the item doesn't exist.

---

## Longitudinal (Layer 10)

### `GET /longitudinal/summaries?limit=10` → `[LongitudinalSummaryOut]`
### `GET /longitudinal/latest` → `LongitudinalSummaryOut` (`404` if none yet)
| field | type |
|---|---|
| `summary_id` | string |
| `week_start_date` / `week_end_date` | iso \| null |
| `session_count` | int |
| `dominant_theme` | string |
| `week_narrative` | string |

> Summaries are generated by the `longitudinal_summary` job (runs on the scheduler, or on demand via
> `POST /admin/jobs/longitudinal_summary`).

---

## Tools (Layer 8)

Natural-language tool requests are detected during `/chat` (`tool_invoked: true`). A fast model
(gemma2:2b) fills the parameters; AUTO actions execute immediately, while SOFT/HARD actions register
a pending confirmation surfaced here.

### `GET /tools/pending` → `[ToolConfirmationOut]`
| field | type | notes |
|---|---|---|
| `request_id` | string | pass to confirm/deny |
| `tool_name` | string | `email`\|`calendar`\|`reminders`\|`notes`\|`web_search` |
| `action_type` | string | |
| `action_description` | string | human-readable |
| `tier` | string | `soft`\|`hard` (real gate) |
| `reversible` | bool | false for irreversible actions (e.g. send email) |

### `POST /tools/confirm/{request_id}` → `ToolResultOut`
Executes the pending action (single-use, ownership-checked). `404` if the id is unknown.
```
{ "ok": bool, "tool_name": string, "operation": string, "outcome": string,
  "result_summary": string, "error_message": string|null }
```

### `POST /tools/deny/{request_id}`
Drops the pending action. `{ "denied": "<request_id>" }`; `404` if unknown.

### `GET /tools/history` → `[ToolActionOut]`
Durable audit of executed actions.
`{ action_id, tool_name, operation, action_type, outcome, result_summary, undone }`

### `POST /tools/undo/{action_id}` → `{ "undone": bool }`
Exposes `ToolManager.undo_action` (implemented and tested before it had a route). `false` if the
tool/action has no reverse operation or the action wasn't found.

---

## Sync (Layer 12 — zero-knowledge)

The server is a **blind relay**: it stores opaque AES ciphertext produced on-device and hands each
device the deltas from *other* devices past its cursor. It never holds the key or decrypts.

### `POST /sync/push` → `SyncPushOut` (`201`)
**`SyncDeltaIn`:** `{ delta_id, source_device, seq, encrypted_payload, size_bytes? }`
(`encrypted_payload` is opaque base64 ciphertext). Idempotent on `delta_id`.
Response: `{ "stored": bool, "delta_id": string }`

### `GET /sync/pull?device_id=<id>&after=<cursor>` → `SyncPullOut`
```
{ "deltas": [ {cursor, delta_id, source_device, seq, encrypted_payload, size_bytes} ], "cursor": int }
```

### `GET /sync/status` → `SyncStatusOut`
`{ "total_deltas": int, "by_device": { device: count }, "latest_cursor": int }`

---

## Admin

### `POST /admin/jobs/{name}` → `JobRunOut`
Run a background job on demand (single-user, no auth). `404` for an unknown job, `500` on failure.
Jobs: **`integrity_check`**, **`memory_consolidation`**, **`proactive_check`**,
**`longitudinal_summary`**, **`pattern_detection`**, **`social_pattern_detection`**,
**`dependency_monitor`**, **`narrative_arc`**, **`life_calendar`**.
```
{ "job": string, "result": { … job-specific summary … } }
```

> The same jobs run automatically on the in-process scheduler (`config.scheduler.enabled: true` by
> default). Set it to `false` to opt out and drive jobs only through this endpoint.

---

## Endpoint index (44 paths)

| Method | Path | Layer |
|---|---|---|
| GET | `/health`, `/health/ready` | infra |
| POST | `/chat`, `/chat/stream` | 1–13 |
| POST | `/voice`, `/voice/transcribe` | 9 |
| GET | `/people`, `/people/{id}` | 5 |
| GET | `/messages`, `/messages/search` | log |
| POST/DELETE | `/messages/{id}/bookmark`, `/messages/{id}/milestone` | log |
| GET | `/bookmarks`, `/milestones` | log |
| GET | `/home`, `/calendar`, `/museum` | continuity |
| GET/POST | `/goals`, `/goals/{id}` | 7 |
| GET/DELETE | `/memory/audit`, `/memory/integrity`, `/memory/search`, `/memory/{id}` | 2/12 |
| GET | `/safety/events` | 11 |
| GET | `/relationship` | 4/5 |
| GET | `/onboarding` | 13 |
| GET | `/sessions` | — |
| GET | `/proactive` | 6 |
| GET | `/longitudinal/summaries`, `/longitudinal/latest` | 10 |
| GET/POST | `/tools/pending`, `/tools/confirm/{id}`, `/tools/deny/{id}`, `/tools/history`, `/tools/undo/{id}` | 8 |
| POST/GET | `/sync/push`, `/sync/pull`, `/sync/status` | 12 |
| POST | `/admin/jobs/{name}` | infra |
