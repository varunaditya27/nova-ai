# Nova — Product Surface (screens → API)

The bridge from the vision docs (`ui-design-reference`, `personality-reference`, `gpt-chat-reference`)
to the live backend. Every planned screen is mapped to the exact endpoint(s) that feed it and tagged:

- ✅ **ready** — endpoint exists today
- 🟡 **building now** — added in this backend pass (see "Backend additions")
- 🔵 **needs backend work** — a real subsystem, scoped as a separate chunk
- ⛔ **deferred** — out of scope for now (per product decision)

**Product spine (from `gpt-chat-reference`, adopted):** the chat is sacred and never accumulates
widgets; every other feature is a **separate lens over the same data**. One permanent conversation —
no "new chat", no folders. In our routing that spine becomes: a marketing **home** (logged-out), an
authenticated **Desk** (logged-in landing), a pure **`/chat`**, and dedicated **lens pages**.

Design direction (decided): **warm study**, ivory-first with brass reserved for *earned* moments;
distinctive free type (Fraunces display + neutral sans body); keep audio (Kokoro voice first).

---

## Routes → screens → endpoints

| Route | Screen | Feeds from | Status |
|---|---|---|---|
| `/` | Marketing home (The Threshold) | (static) | ✅ **built** |
| `/desk` | **Digital Desk** — greeting, current chapter, held thought, weather, continue | `GET /home` | ✅ **built** |
| `/chat` | The one permanent conversation (history, streaming, echoes, voice) | `GET /messages`, `POST /chat/stream` (direct) + `POST /chat` fallback | ✅ **built** |
| `/chat` (search) | ⌘K keyword + date search | `GET /messages/search` | ✅ **built** |
| `/chat` (AI search) | ⌘K "the time I was scared" semantic search | `GET /memory/search` | ✅ **built** |
| `/life` | Life timeline — weekly chapters as a vertical thread | `GET /longitudinal/summaries` + `/latest` | ✅ **built** |
| `/life/calendar` | Activity heatmap (per-day, color-mix intensity) | `GET /calendar` | ✅ **built** |
| `/life/museum` | "Firsts" — brass-labelled earned moments | `GET /museum` | ✅ **built** |
| `/memories` | Episodic + semantic vault, integrity badge, two-step forget | `GET /memory/audit`, `/memory/integrity`, `DELETE /memory/{id}` | ✅ **built** |
| `/bookmarks` | Saved messages; toggled from chat hover | `GET /bookmarks`, `POST/DELETE /messages/{id}/bookmark` | ✅ **built** |
| `/milestones` | Life-moment album; toggled from chat hover | `GET /milestones`, `POST/DELETE /messages/{id}/milestone` | ✅ **built** |
| `/goals` | Goals + progress meters, add-a-goal | `GET /goals`, `POST /goals` | ✅ **built** |
| `/relationship` | Stage progression + learned communication-style meters | `GET /relationship` | ✅ **built** |
| `/proactive` | Threads Nova is holding | `GET /proactive` | ✅ **built** |
| `/voice` | Speak a reply (Nova's voice) | `POST /voice` | ✅ |
| `/privacy` | Both hash chains + zero-knowledge sync status | `GET /memory/integrity`, `GET /sync/status` | ✅ **built** |
| `/media` | Images / voice notes / files gallery | — | 🔵 attachments subsystem |
| `/people` | Social graph of people the user mentions | — | ⛔ deferred |
| | `/admin` | Machine room — run background jobs | `POST /admin/jobs/{name}` | ✅ **built** |

**Echoes** (`gpt-chat-reference` Principle 7 — the highest wow-to-effort idea): every `/chat` reply and
every message in history now carries the memories Nova recalled while writing it — the backend already
computes them per turn; they are exposed on `ChatResponse.echoes` and each Nova `MessageOut.echoes`.

---

## Backend additions (this pass)

### New: conversation message log (unblocks `/chat`)
The backend persisted episodic *summaries* + per-session turn counts, but **no retrievable
transcript**. Added `conversation_message` (`infra/db/models/message.py`) + `PostgresMessageStore`,
written every turn by `make_message_writer` (persists the user message and Nova's reply, with turn
metadata + recalled-memory **echoes**). One user-scoped thread (the product's "one permanent chat").

- `GET /messages?limit=&before=<id>` → newest-first page of `MessageOut` (role, content, ts, mode,
  crisis/tool flags, echoes, bookmarked, is_milestone).
- `GET /messages/search?q=&start=&end=&limit=` → deterministic keyword + date-range search.
- `GET /memory/search?q=&limit=` → semantic ("AI") search over episodic memory via the embedding/ANN
  path (distinct from keyword search, as the vision doc wants).

### New: message annotations (bookmarks + milestones)
- `POST /messages/{id}/bookmark` `{category?}`, `DELETE /messages/{id}/bookmark`, `GET /bookmarks?category=`
- `POST /messages/{id}/milestone` `{label?}`, `DELETE /messages/{id}/milestone`, `GET /milestones`

### New: continuity aggregation (mostly derived over existing data)
- `GET /home` → Digital Desk: greeting band, current chapter (latest longitudinal narrative), top
  proactive candidate(s), active-goal count, relationship stage + `last_interaction_at` + a derived
  "weather", cold-start flag.
- `GET /calendar?start=&end=` → per-day activity counts + dominant emotion (heatmap).
- `GET /museum` → "firsts" derived from the message log + milestones + goals.

### Scoped separately (not in this pass)
- 🔵 **Attachments / media** (`/media`, voice-note & file storage): needs a storage decision
  (Postgres large-object vs. Layer-12 on-device encrypted store) and, for *understanding* images/PDFs,
  a vision-capable model (current local model is text-only). Worth its own chunk.
- ⛔ **People / social graph** (`/people`): Layer-5 exists internally but is intentionally deferred.
- **Life Graph / Universe** (`gpt-chat-reference` Principle 9/10): the north-star demo; needs an
  entity-relationship graph API + heavy client work. Keep as a vision target, not a v1 commitment.

---

## Notes for the frontend
- **One thread.** `GET /messages` returns the whole relationship, paginated by `before=<id>` — the UI
  navigates by search / jump / continue-from-bottom, never by long scrolling.
- **Never inject insights into the chat** (Principle: no "💡 Memory" / "Goal progress" mid-conversation).
  Echoes are the *one* allowed ambient element, and they're tiny + dismissible.
- **Empty states are the product.** Day one has nothing to remember; every lens must be beautiful when
  empty and grow richer over time. Silence is a feature.
- Full schema/endpoint detail: [`docs/API_REFERENCE.md`](../docs/API_REFERENCE.md) and `GET /openapi.json`.
