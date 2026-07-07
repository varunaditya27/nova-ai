# Nova Frontend — Slice 1: The Spine (design)

**Date:** 2026-07-08
**Status:** approved, pre-implementation
**Scope:** the first vertical slice of the Nova frontend — `/` (Threshold) → `/desk` (Digital Desk)
→ `/chat` (The Conversation) — built against the live backend (35 routes, `docs/API_REFERENCE.md`).
This slice establishes the whole design language (type, material, motion, sound) and the API
integration spine; the lens pages (`/life`, `/memories`, `/goals`, `/relationship`, …) are later
slices that *replicate* this proven language and are out of scope here.

---

## 1 · Soul (the non-negotiable feeling)

From `frontend/personality-reference.md` + `frontend/ui-design-reference.md`:

- **Belief:** *"Intelligence should feel like a relationship, not a tool."* The interface looks
  **inevitable**, not intelligent — so restrained the intelligence only reveals itself through use.
- **Room:** a **private study** — somewhere you go to *think*, not to consume.
- **Tempo:** confidently unhurried. Nothing flashes, bounces, or panics. Things **arrive because
  they were ready**. Loading is a calm settling, never a spinner that panics.
- **Material, not gradient:** paper, ink, metal, light. UI that feels **carved**, not painted.
  Depth via *contrast*, not shadow. Radii 6–14px. One hairline border weight.
- **Vocabulary:** human verbs only — *remembers, notices, wonders, continues, grows*. Banned forever:
  "AI-powered," "revolutionary," "next-gen," "state of the art."
- **Character:** curious, observant, quietly funny, never loud, never oversells.
- **The one permitted magic:** **echoes** — the memories Nova recalled while writing a reply.
  Nothing else is injected into the chat (no "💡 Memory", no "Goal progress" widgets).

## 2 · Foundational decisions (settled)

| Decision | Choice |
|---|---|
| Framework | **Next.js (App Router)**, TypeScript |
| Aesthetic soul | **Ivory + Ink** (paper/library), with a true **Obsidian dark study mode** as its faithful shadow |
| Brass | **earned accent only** — milestones, firsts, bookmarks — in both themes |
| Display type | **Fraunces** (variable: optical-size + SOFT axes) — warm editorial serif |
| Body/UI type | **Switzer** (variable grotesk, self-hosted) — warmer than Inter/Geist |
| Mono | **Geist Mono** — rare tabular/code; tabular figures everywhere |
| Styling | **Tailwind v4** (`@theme`) over a **strict design-token layer** — no arbitrary values |
| Motion | **`motion` (Framer Motion)** — springs only, no CSS easing |
| Server state | **TanStack Query** for REST; native `fetch` + `ReadableStream` for SSE |
| Sound | **Web Audio** `useAcoustics` — default on, whisper-quiet, obvious mute, auto-muted under `prefers-reduced-motion` |
| API access | **Next rewrites** `/api/* → ${NEXT_PUBLIC_API_BASE:-http://127.0.0.1:8000}/*` (same-origin browser calls; auth slots in at the Next edge later) |

### Palette tokens

```
IVORY + INK  (soul)        DARK STUDY (shadow)
 paper    #F4F1EA           bg      #0B0B0D
 surface  #FBFAF6           surface #141317
 raised   #FFFFFF           raised  #1C1B20
 ink      #1A1714           text    #ECE7DE
 ink-soft #4A443C           text-soft #A29C90
 hairline #E3DDD0           hairline #2A2830
 brass    #9A7B4F           brass    #C9A96A   (earned only)
```
Contrast is validated to WCAG-AA on both themes. No shadows except a single near-invisible
contact shadow token; elevation is expressed with `raised`/`hairline`/contrast.

## 3 · Repository layout

The Next app lives in `frontend/`. Existing vision `.md` docs move to `frontend/reference/`
(`personality-reference.md`, `ui-design-reference.md`, `gpt-chat-reference.md`); `PRODUCT_SURFACE.md`
and `DEFERRED_WORK.md` stay at `frontend/` root (they're live product docs).

```
frontend/
  app/
    layout.tsx            # fonts, theme + acoustics providers, dock
    page.tsx              # /  The Threshold
    desk/page.tsx         # /desk  The Digital Desk
    chat/page.tsx         # /chat  The Conversation
  components/
    primitives/           # Surface, CarvedButton, Dock, ThreadLine, EchoChip, CommandSurface, Hairline
    chat/                 # Composer, MessageStream, EchoRail, VoiceButton
    desk/                 # GreetingBand, CurrentChapter, HeldThought, Weather
    marketing/            # Belief, HumanVerbs, BeginCTA
  lib/
    api/                  # typed client (client.ts, types.ts) derived from API_REFERENCE.md
    hooks/                # useChatStream, useMessages, useHome, useVoice, useAcoustics, useTheme
    tokens.css            # design tokens (CSS vars) consumed by @theme
    acoustics/            # tiny generated audio samples + player
  reference/              # moved vision docs
  next.config.ts          # rewrites, font/image config
  package.json
```

## 4 · Design language / primitives (seed of the design bible)

Every future lens page reuses these. Each is a small, independently-understandable unit:

- **`Surface`** — a carved panel. Wakes on cursor approach (tiny lighting shift, spring), sleeps on
  leave. `raised` variant for the one-level-up feeling. No drop shadow.
- **`CarvedButton`** — inner highlight + subtle outer stroke; tactile press (spring scale ≤ 0.98).
  Brass variant reserved for earned actions.
- **`Dock`** — floating Arc-style nav (not a sidebar). Slice 1: **Desk / Chat**; lens routes render
  as *coming* (dimmed, non-navigating).
- **`ThreadLine`** — bubble-less turn: `You` / hairline / `Nova`. Timestamp on hover only.
- **`EchoChip` / `EchoRail`** — tiny, dismissible recalled-memory markers under a Nova turn.
- **`CommandSurface`** — ⌘K palette (Raycast-like) holding keyword search, semantic search, and jump.
  Never clutters the thread.
- **Paper grain** — a single near-invisible SVG/noise layer behind `paper`; absent in dark mode
  (replaced by a faint obsidian sheen token).

**Motion grammar:** enter = settle (spring, low stiffness, no overshoot on content); hover = wake
(opacity/`raised` shift); press = tactile; route change = cross-fade + slight rise. Reduced-motion
path swaps all of it for instant, opacity-only transitions.

**Acoustics:** open chime (app mount), paper-click (save/bookmark), soft room tone (voice playback).
Generated at build via Web Audio offline render into small assets. Global mute + persisted preference.

## 5 · Screens

### `/` The Threshold (feeling: *curious*)
Single unhurried composition — no feature grid, no gradient, no floating cards:
- one **statement of belief**, set in Fraunces;
- one honest line of **human verbs** (*It remembers. It notices. It continues.*);
- one restrained CTA **Begin** (`CarvedButton`) → `/desk`;
- private-study material: paper grain, one carved brass detail, generous silence.
Static — no API calls.

### `/desk` The Digital Desk (feeling: *comfortable, continuous*)
Feeds a single `GET /home` → `HomeOut`:
- **GreetingBand** — `greeting` ("Good evening") in Fraunces.
- **CurrentChapter** — `current_chapter` (latest longitudinal theme) or a calm empty line.
- **HeldThought** — `top_proactive` rendered quietly ("A thought I've been holding…"); hidden if null.
- **Weather** — `weather` + `relationship_stage` + `last_interaction_at` as one ambient line.
- **Continue** — `CarvedButton` → `/chat`.
- **Empty state (day one):** `message_count === 0` → *"This is where your life together will gather."*
- Brass appears only if an earned milestone is present.

### `/chat` The Conversation (feeling: *understood*) — the sacred space
- **History:** `GET /messages?limit=&before=<cursor>`, newest-first, rendered oldest→newest,
  **continue-from-bottom**; page back by passing the top item's `cursor` as `before`. A page shorter
  than `limit` = start of the relationship.
- **Send:** `POST /chat/stream` (SSE `meta` → `token`×N → `done`); `useChatStream` reduces frames to
  live text using each token's `delay_ms` (Layer-9 pacing). Concatenated tokens == delivered text
  (honors SC-1-before-Layer-9). Terminal `error` frame → fall back to `POST /chat` (non-stream).
- **Render:** `ThreadLine` (no bubbles), timestamps on hover.
- **Echoes:** from the `meta`/`done` payload's turn + the persisted `MessageOut.echoes`; shown as a
  dismissible `EchoRail` under the Nova turn. When `confabulation_guard` is true there are none — and
  we never invent them.
- **Search (⌘K `CommandSurface`):** keyword+date `GET /messages/search`; semantic
  `GET /memory/search`. Results jump the thread to a message; never render inside it.
- **Voice:** a quiet `VoiceButton` on a Nova turn → `POST /voice` (`audio/mpeg`); `503` → stays text.
- **Empty state (day one):** a single invitation line; the composer is the only affordance.

## 6 · Data flow & integration

- **Typed API client** (`lib/api/`) — one function per used endpoint, hand-derived from
  `docs/API_REFERENCE.md`; typed responses (`HomeOut`, `MessageOut`, `Echo`, `ChatMeta`, …).
- **TanStack Query** for `GET /home`, `GET /messages` (infinite query on `before`). Bookmark/
  milestone *mutations* are **out of scope for this slice** (they belong to the `/bookmarks` /
  `/milestones` lens pages); the read fields (`bookmarked`, `is_milestone`) are still rendered.
- **`useChatStream`** — a reducer over SSE frames: `idle → meta → streaming(text) → done(echoes)`;
  exposes live text, mode/system, and final echoes; optimistic-appends the user turn immediately.
- **CORS:** add the dev origin to `config.api.cors_origins`, but browser traffic goes through Next
  rewrites so it's same-origin regardless.

## 7 · Error handling, a11y, performance

- **Graceful degradation everywhere:** stream→`/chat`, voice→text, any list→empty state. No raw
  error dumps; calm inline copy ("I lost the thread there — try again?").
- **A11y:** semantic landmarks, visible focus, `prefers-reduced-motion` path, AA contrast both themes,
  ⌘K reachable by keyboard, live-region announce for streaming completion.
- **Performance:** self-hosted variable fonts with `font-display: swap` + preloaded; grain is one
  static asset; springs are GPU-friendly transforms; no layout thrash during streaming (append-only).

## 8 · Testing

- **Vitest + Testing Library:** `useChatStream` reducer (frame ordering, token concat == text,
  error→fallback), echo projection, cursor pagination merge.
- **Playwright smoke (1):** Threshold → Begin → Desk → Chat → send → tokens stream in → an echo
  appears (or confabulation-guard shows none) — against the live backend on `:8000`.
- Frontend tests are separate from the Python offline suite; they do not touch the `pytest` gate.

## 9 · Build sequence (becomes the plan)

1. Scaffold Next.js (App Router, TS) in `frontend/`; move vision docs to `frontend/reference/`.
2. Tokens + fonts + theme provider + `useAcoustics` + motion setup.
3. Core primitives (`Surface`, `CarvedButton`, `Dock`, `ThreadLine`, `EchoChip/Rail`, `CommandSurface`).
4. Typed API client + Next rewrites + TanStack Query provider.
5. `useChatStream` + `useMessages` + `useHome` + `useVoice`.
6. `/` Threshold.
7. `/desk` Digital Desk (+ empty state).
8. `/chat` Conversation (history, streaming, echoes, ⌘K search, voice, empty state).
9. Craft pass — paper grain, spring tuning, hover-wake, acoustics, dark mode parity.
10. Vitest unit tests + one Playwright smoke.

## 10 · Out of scope (deferred to later slices)

Lens pages `/life`, `/life/calendar`, `/life/museum`, `/memories`, `/goals`, `/relationship`,
`/proactive`, `/bookmarks`, `/milestones`, `/privacy`, `/admin`; auth/multi-user; media/attachments;
people/social graph; WebSocket transport; STT/mic input. See `frontend/DEFERRED_WORK.md` and
`frontend/PRODUCT_SURFACE.md`. These reuse the design language proven by this slice.
