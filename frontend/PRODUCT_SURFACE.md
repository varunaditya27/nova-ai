# Nova — Product Surface (screens → API)

Every screen of the web app and the backend endpoints that feed it. All endpoints the app uses are
live; the routes are the single source of truth in `lib/nav.ts`. Full schemas:
[`docs/API_REFERENCE.md`](../docs/API_REFERENCE.md).

**Product spine:** one permanent conversation (Talk) that never accumulates widgets; every other
page is a separate lens over the same data. No "new chat", no folders.

**Design direction:** *the light follows your real day.* `data-light` (dawn / day / dusk / night) is
stamped on `<html>` from the local hour (`components/ThemeProvider.tsx`, no-flash inline script, manual
override in the sidebar). Flat tone steps instead of lines or shadows (shadows only on floating
sheets/menus/toasts), two typefaces (Young Serif display, Literata body), five type sizes, accent
rani-pink, marigold reserved for moments that mattered. No chat bubbles. Copy is plain language: no
enum values, ISO timestamps, or decimals reach the screen (mapping tables in `lib/*.ts`, each tested).

## Routes → endpoints

| Route | Screen | Endpoints |
|---|---|---|
| `/welcome` | First-run front door (shown once, until the first message) | `GET /home` |
| `/` | **Talk** — history, streamed replies, echoes, read-aloud, jump-to-message, Nova's opening line | `GET /home`, `GET /messages`, `POST /chat/stream` (direct to API), `POST /voice`, `POST /voice/transcribe`, `GET /proactive`, `GET /proactive/stream`, `POST /proactive/{id}/delivered`, `GET /tools/pending`, `POST /messages/{id}/bookmark\|milestone` (+`DELETE`) |
| Search (Ctrl/⌘K) | Jump to a page, find exact words, or search by meaning | `GET /messages/search`, `GET /memory/search` |
| `/today` | What's on Nova's mind, what's coming up | `GET /home`, `GET /proactive`, `GET /goals`, `GET /people` |
| `/story` | Chapters / Days / Firsts | `GET /longitudinal/summaries`, `GET /longitudinal/latest`, `GET /calendar`, `GET /museum` |
| `/keepsakes` | Moments that mattered / Saved messages | `GET /milestones`, `GET /bookmarks`, `DELETE /messages/{id}/milestone\|bookmark` |
| `/memory` | What Nova remembers; two-step forget with a signed receipt | `GET /memory/audit`, `GET /memory/{id}`, `GET /memory/search`, `DELETE /memory/{id}` |
| `/people`, `/people/[id]` | People Nova has come to know; their events and patterns | `GET /people`, `GET /people/{id}` |
| `/goals`, `/goals/[id]` | Goals, milestones, habits; add / pause / complete / remove | `GET /goals`, `GET /goals/{id}`, `POST /goals`, `PATCH /goals/{id}`, `DELETE /goals/{id}` |
| `/errands` | Pending confirmations, history, undo | `GET /tools/pending`, `POST /tools/confirm\|deny/{id}`, `GET /tools/history`, `POST /tools/undo/{id}` |
| `/us` | How well Nova knows you; learned communication style; chat sessions | `GET /relationship`, `GET /onboarding`, `GET /sessions` |
| `/care` | Times Nova checked in on you, and who to call | `GET /safety/events` |
| `/privacy` | Both tamper-evident chains, sync status | `GET /memory/integrity`, `GET /sync/status` |
| `/upkeep` | Nova's housekeeping jobs, run by hand; service health | `POST /admin/jobs/{name}`, `GET /health/ready` |

Backend is single-user with no auth; the Next server proxies `/api/*` to the FastAPI app
(`next.config.ts`). The two streaming calls (`/chat/stream`, `/proactive/stream`) go direct to
`NEXT_PUBLIC_API_BASE` because the dev proxy buffers SSE.

## Notes
- **One thread.** `GET /messages` returns the whole relationship, paginated by `before=<id>`; the UI
  navigates by search / jump / scroll-up, never long scrolling.
- **Never inject insights into the chat.** Echoes (memories Nova recalled for a reply) are the one
  allowed ambient element; they're small and dismissible.
- **Empty states are the product.** Day one has nothing to remember; every page is written for empty
  and grows richer with time.
- **Not built (needs backend first):** attachments/media gallery (no storage or vision model), a
  life-graph visualisation.
