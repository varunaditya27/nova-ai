# Nova — Deferred Work Register

Everything intentionally **not** built yet, gathered across all planning discussions, so the backend's
boundaries are explicit before frontend work begins. Nothing here is broken or half-done — these are
*scoped-out* items. What **is** built and live is the 35-route surface in
[`../docs/API_REFERENCE.md`](../docs/API_REFERENCE.md); the screen→endpoint map is
[`PRODUCT_SURFACE.md`](PRODUCT_SURFACE.md).

Legend — **why deferred**: `DECISION` (product choice), `DESIGN` (needs a design decision first),
`ROADMAP` (documented future), `POLISH` (nice-to-have), `PROD` (production hardening).

---

## 1. Auth & multi-user  — `DECISION`
- **State:** no authentication. Single user via `config.system.default_user_id` (env `NOVA_USER_ID`).
- **When it lands, also do:** the read/mutate-by-id routes (`GET /goals/{id}`, `GET/DELETE /memory/{id}`,
  `GET /messages`→annotate) resolve by id **without a user filter** — safe under single-user, but must
  become user-scoped to prevent IDOR. All *list* routes are already user-scoped via the stores.
- **Needs:** `api/routes/auth.py` (currently a stub), password hashing + JWT/session, a per-request
  `current_user` dependency replacing `default_user_id`, and per-user CORS/cookie handling.
- **Size:** medium. **Blocks frontend?** No — build single-user first, add an auth gate later.

## 2. Media / attachments (`/media`)  — `DESIGN`
- **State:** no attachment storage or upload; `/media` would be empty. Chat is text-only.
- **Why deferred:** the **ingestion pipeline must be designed first** — (a) storage backend
  (Postgres large-object vs. the Layer-12 on-device SQLCipher store vs. object storage), (b) encryption
  at rest, (c) upload/serve endpoints + size/type limits + scanning, and (d) for *understanding* images
  or PDFs, a **vision-capable model** (the local model is text-only). Storage/gallery and understanding
  are separable and should be scoped separately.
- **Needs:** an `attachment` model + store, `POST /attachments` (multipart) + `GET /attachments/{id}`,
  message↔attachment linkage, and a Layer-1 multimodal path for understanding.
- **Size:** large (its own chunk). **Blocks frontend?** No — the other lenses stand alone.

## 3. People / social graph (`/people`)  — `DECISION`
- **State:** Layer 5 maintains a social graph internally; **no API exposes it**.
- **Why deferred:** explicitly out of scope for now.
- **Needs:** a people/relationships read model + `GET /people`, `GET /people/{id}` (summary, timeline,
  shared mentions), projecting the Layer-5 graph + UWM relationship nodes.
- **Size:** medium. **Blocks frontend?** No.

## 4. Life Graph / "Universe" view  — `ROADMAP`
- The gpt-chat-reference north-star (Principles 9–10): an explorable entity-relationship graph of the
  user's life (projects ↔ people ↔ goals ↔ memories), zoomable, re-centring on any node.
- **Why deferred:** needs an entity-graph API that doesn't exist (depends on #3 + a memory-association
  graph) and heavy client work. Keep as the aspirational demo, not a v1 commitment.
- **Size:** very large. **Blocks frontend?** No — the WhatsApp-simple chat is the v1 core.

## 5. Transport & delivery  — `ROADMAP`
- **WebSocket** transport — SSE (`/chat/stream`) is live and sufficient; WS is the future bidirectional
  upgrade (interrupts, live voice).
- **Proactive push channel** — done (2026-08-09): `GET /proactive/stream` (SSE, bounded ~25min
  lifetime relying on `EventSource` auto-reconnect) + `useProactiveStream`/`app/proactive/page.tsx`
  consume it live, alongside the existing poll. True OS-level push notification (outside an open
  tab) still needs web-push infra — that part remains deferred.
- **Speech-to-text (voice input)** — `/voice` is TTS **output** only; there is no transcription of
  spoken user input. Needs an STT model/endpoint.

## 6. Onboarding & persona depth  — `ROADMAP`
- **Layer-13 feature-pacing** — active elicitation is done (one earned question/session); *progressive
  feature introduction* (revealing capabilities as the relationship matures) is not wired.
- **Elicitation answer-capture** — Nova surfaces onboarding questions and never repeats them, but does
  **not yet extract/infer the answer** from the user's reply (the Layer-13 `passive_elicitation`
  extractors aren't wired to write the inferred value back). Today it asks; it doesn't yet *learn* the
  answer automatically.
- **Deeper persona learning** — four communication-style params are learned (verbosity, formality,
  question/advice tolerance); richer preference/personality modelling is future.

## 7. Continuity flourishes (from gpt-chat-reference)  — `POLISH`
Built: Digital Desk (`/home`), calendar heatmap (`/calendar`), museum of firsts (`/museum`), echoes,
milestones, bookmarks, timeline via `/longitudinal`. Not built (nice-to-haves):
- **Calendar emotional overlay** — `/calendar` returns message *counts*; "most emotional day / most
  productive day" needs per-day valence/emotion aggregation (from Layer-3 signals + safety log).
- **Richer museum firsts** — first joke / first disagreement / first "proud of you" need semantic
  first-detection; today's museum covers first conversation / first milestone / first goal.
- **Echo "when" for recent memories** — the human label (`when`) is populated from Layer-2's fuzzy
  temporal label; very recent memories may have none yet.
- **Seasons, Time Machine, Wrapped/soundtrack, relationship "weather" for people** — narrative synthesis
  features; each needs a generation job + (for people) #3.

## 8. Search depth  — `POLISH`
- Keyword search (`/messages/search`) and semantic memory search (`/memory/search`) are live. A richer
  **conversational retrieval** ("that time I was scared" spanning multiple turns with reranking) is a
  future enhancement over the current ANN-over-episodic approach.

## 9. Production hardening  — `PROD`
- **Cloud System-2** — closed decision, not deferred: the platform runs fully offline on local Ollama
  models (`config/defaults.yaml`, `NOVA_MAIN_MODEL`/`NOVA_MINI_MODEL`), no cloud LLM provider at all.
- **Migrations** — persistent schema currently rides the Alembic **baseline `create_all`** (every model
  is picked up); a production cutover to incremental, autogenerated migrations is future work.
- **Rate limiting, request quotas, audit/observability, secrets management, TLS/gateway** — none present
  (local single-user dev posture).
- **Attachment safety** (scanning, size caps) — part of #2.

---

## Not deferred — done & frontend-ready
Chat (+SSE, echoes, gemma tool-intent), the permanent **message log** (history/search/annotations),
goals, memory (audit/integrity/semantic-search/forget), safety events, relationship + **learned persona
params**, onboarding + **active elicitation**, sessions, **proactivity into the turn**, longitudinal,
**voice (Kokoro)**, sync (zero-knowledge), **Digital Desk / calendar / museum**, admin jobs, and the
scheduler (on by default). Input validation, error semantics (404/422/503), pagination cursors, and
CORS-from-config are all verified live. See `../docs/API_REFERENCE.md`.
