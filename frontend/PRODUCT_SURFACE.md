# Nova — Product Surface (screens → API)

Every screen of the web app and the backend endpoints that feed it. All endpoints the app uses are
live; the routes are the single source of truth in `lib/nav.ts`. Full schemas:
[`docs/API_REFERENCE.md`](../docs/API_REFERENCE.md).

**Product spine:** one permanent conversation (Talk) that never accumulates widgets; every other
page is a separate lens over the same data. No "new chat", no folders.

**Shape language: the star-cut.** Nothing is a pill or a soft rounded box. Every button, card, field and nav item is a plain rectangle with the four concave points of Nova's star bitten out of its corners (`.cut-sm` / `.cut` / `.cut-lg` in `app/globals.css`, drawn with a CSS mask so the cut is exact at any size and focus rings sit inside it). Circles are reserved for the knots of the thread. Editorial structure comes from rules, numbered chapters (`01 · The proof`) and one oversized display face. Buttons fill with ink from the left on hover; tabs are underlined, not pills. Shared brand layer (smooth scroll, grain, cursor) lives in `components/brand/` and is mounted by `AppShell` for every page.

**Design direction:** *the light follows your real day.* `data-light` (dawn / day / dusk / night) is
stamped on `<html>` from the local hour (`components/ThemeProvider.tsx`, no-flash inline script, manual
override in the sidebar). Flat tone steps instead of lines or shadows (shadows only on floating
sheets/menus/toasts), two typefaces (Young Serif display, Literata body), five type sizes, accent
rani-pink, marigold reserved for moments that mattered. No chat bubbles. Copy is plain language: no
enum values, ISO timestamps, or decimals reach the screen (mapping tables in `lib/*.ts`, each tested).

## Routes → endpoints

| Route | Screen | Endpoints |
|---|---|---|
| `/welcome` | Cinematic product landing page (see "Landing page" below). Shown once on first run, reachable by address afterwards. No sidebar. | none (static; the first-run redirect on `/` reads `GET /home`) |
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

## Landing page (`/welcome`)

**Motion identity** (the `motion-design` skill's *Premium* archetype): calm, elegant, nothing overshoots. One
entrance everywhere (`focusPull` in `lib/motion.ts`: slightly low, slightly small, out of focus, then settled), entrances
decelerate on `power4.out`, moves between states ease both ends, durations are 0.35 / 0.5 / 0.8 s. Every scene has a
main action, a supporting detail and a slow ambient layer. Nothing is `linear` except things tied directly to scroll.

**The opening shot is a film**, not a web animation: `film/` holds the Remotion source (1920×1080, 10 s, a day passing over one
life, seamless loop); it is graded in ffmpeg and shipped as `public/film/hero.{mp4,webm}` (+ `hero-sm.*` for phones, + a poster).
It plays only on screen, and is a still for anyone who prefers less motion.

**Scroll score**, in order (researched: no scroll-jacking, every pin has a clear release, no more than two pins, high-impact
transitions only at hand-offs, desktop choreography simplifies on small screens):

| Act | Behaviour |
|---|---|
| Title sequence | Once per visit: the star ignites, the name appears, the curtain lifts. The hero waits for it. |
| Opening | Camera pushes in and the copy lifts away as you leave (counter-motion); a pool of light follows the pointer. |
| Ribbon | The four verbs drift; scrolling speeds it up and leans it. |
| The proof | One thread draws as you scroll; the reply is read word by word. |
| The difference | Words come up in turn; the two cards move at different speeds (depth). |
| How it grows | **Pinned.** Scroll moves through four stages and the room's light goes dawn → night. Stacked on phones. |
| How it connects | Section opens from a card to full width; edges draw; points react to touch. |
| What it does | **Pinned, horizontal reel** of six moving pictures of real screens. Stacked on phones. |
| Privacy | Opens like the section above; try-it tamper chain. |
| Chapter rail | Right edge, wide screens: a sun rides a line as you scroll and marks the chapter you are in; it doubles as a contents list. |

Tooling: GSAP (ScrollTrigger, SplitText), Lenis smooth scroll (off for reduced motion), `motion/react`, Remotion (film only). `prefers-reduced-motion`:
no smooth scroll, no pinning, no scrubbing, still film, content simply sits in its final state.

## Notes
- **One thread.** `GET /messages` returns the whole relationship, paginated by `before=<id>`; the UI
  navigates by search / jump / scroll-up, never long scrolling.
- **Never inject insights into the chat.** Echoes (memories Nova recalled for a reply) are the one
  allowed ambient element; they're small and dismissible.
- **Empty states are the product.** Day one has nothing to remember; every page is written for empty
  and grows richer with time.
- **Not built (needs backend first):** attachments/media gallery (no storage or vision model), a
  life-graph visualisation.
