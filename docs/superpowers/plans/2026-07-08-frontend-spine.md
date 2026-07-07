# Nova Frontend — Slice 1 (The Spine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the frontend product spine — `/` (Threshold) → `/desk` (Digital Desk) → `/chat` (The Conversation) — as a Next.js 16 app wired to the live backend, establishing the ivory-first "warm study" design language every later lens page reuses.

**Architecture:** Next.js 16 App Router (React 19, TS) in `frontend/`. A strict design-token layer (Tailwind v4 `@theme` over CSS vars) drives ivory + dark themes; `motion` springs for all animation; `@fontsource-variable` self-hosted fonts. A thin typed API client + TanStack Query hit the backend through Next rewrites (`/api/* → :8000`); `/chat/stream` is consumed as raw SSE by a `useChatStream` reducer.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS v4, `motion` 12, `@tanstack/react-query` 5, `@fontsource-variable/fraunces` + `@fontsource-variable/instrument-sans` + `geist` (mono), Vitest + Testing Library, Playwright.

## Global Constraints

- **Aesthetic:** ivory-first warm-study; **brass (`#9A7B4F` / dark `#C9A96A`) is earned-only** (milestones/firsts/bookmarks) — never decorative. Radii 6–14px. Depth via contrast, not shadow. No gradients, no glass, no floating particles.
- **Copy:** human verbs (remembers, notices, continues). **Banned words:** "AI-powered", "revolutionary", "next-gen", "state of the art".
- **Motion:** springs only (no CSS easing); content settles, never flies. Full `prefers-reduced-motion` path (opacity-only / instant).
- **No font CDN:** all fonts via bundled npm packages. **No build-time network to font hosts.**
- **Chat is sacred:** no bubbles (You / hairline / Nova), timestamps on hover only; **echoes are the ONLY ambient injection**; never invent echoes when `confabulation_guard` is true.
- **Graceful degradation:** stream→`POST /chat`, voice→text, every list→a beautiful empty state. No raw error dumps.
- **A11y:** semantic landmarks, visible focus, AA contrast both themes.
- Backend contracts are fixed — see `docs/API_REFERENCE.md`. Frontend tests are separate from the Python `pytest` gate.

---

### Task 1: Scaffold + proxy + dependencies

**Files:**
- Create: `frontend/` Next.js app (`package.json`, `tsconfig.json`, `next.config.ts`, `app/layout.tsx`, `app/page.tsx`, `app/globals.css`, `.gitignore`, `eslint.config.mjs`, `postcss.config.mjs`)
- Move: `frontend/{personality,ui-design,gpt-chat}-reference.md` → `frontend/reference/`

**Interfaces:**
- Produces: a booting dev server; `GET /api/health` proxied to backend `:8000` returns `{"status":"ok"}`.

- [ ] Scaffold into a temp dir then move into `frontend/` (create-next-app refuses a non-empty target): `npx create-next-app@latest /tmp/nova-fe --ts --app --tailwind --eslint --no-src-dir --import-alias "@/*" --turbopack --use-npm --yes`, then move all generated files (incl. dotfiles) into `frontend/`.
- [ ] Move the three vision reference docs into `frontend/reference/`.
- [ ] Install runtime deps: `npm i motion @tanstack/react-query @tanstack/react-query-devtools @fontsource-variable/fraunces @fontsource-variable/instrument-sans geist`.
- [ ] Install dev/test deps: `npm i -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom @playwright/test`.
- [ ] `next.config.ts`: add rewrite `{ source: "/api/:path*", destination: "${NEXT_PUBLIC_API_BASE || http://127.0.0.1:8000}/:path*" }`; read base from env with the `127.0.0.1:8000` default.
- [ ] Add `.env.local` (git-ignored) with `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`; ensure `.env.local` is in `.gitignore`.
- [ ] Verify: `npm run dev` boots; `curl -s localhost:3000/api/health` → `{"status":"ok"}`.
- [ ] Commit `feat(frontend): scaffold Next.js 16 app + backend proxy`.

### Task 2: Design tokens + themes + fonts + paper grain

**Files:**
- Create: `frontend/lib/tokens.css` (CSS vars for both themes), `frontend/lib/fonts.ts`, `frontend/components/ThemeProvider.tsx`, `frontend/public/grain.svg`
- Modify: `frontend/app/globals.css` (import tokens, `@theme` mapping, base layer), `frontend/app/layout.tsx` (fonts + providers)

**Interfaces:**
- Produces: CSS vars `--paper --surface --raised --ink --ink-soft --hairline --brass` under `:root` (ivory) and `[data-theme="dark"]`; Tailwind utilities `bg-paper text-ink border-hairline text-brass` etc.; `useTheme()` → `{ theme, toggle }` persisted to `localStorage`, respecting `prefers-color-scheme` on first load.

- [ ] `tokens.css`: define both palettes (values from spec §2) + spacing/radii scale (`--r-sm:6px … --r-lg:14px`) + one contact-shadow token.
- [ ] `globals.css`: `@import "tailwindcss";` then `@theme inline { --color-paper: var(--paper); … }` so utilities resolve to tokens; base body = `bg-paper text-ink font-body antialiased`; tabular figures default.
- [ ] `fonts.ts`: import `@fontsource-variable/fraunces` + `@fontsource-variable/instrument-sans` + `GeistMono`; expose CSS var class names `--font-display --font-body --font-mono`.
- [ ] `layout.tsx`: apply font vars to `<html>`, wrap children in `ThemeProvider`; set `<html lang="en" suppressHydrationWarning>`.
- [ ] `ThemeProvider`: inline no-flash script that reads `localStorage.theme` / `matchMedia` and stamps `data-theme` before paint; context exposes `toggle`.
- [ ] `grain.svg`: feTurbulence noise at ~3% opacity; applied as a fixed body::before in ivory only.
- [ ] Verify visually via a temporary swatch on `/`; toggle flips ivory↔dark with no flash.
- [ ] Commit `feat(frontend): design tokens, ivory+dark themes, fonts, paper grain`.

### Task 3: Acoustics (Web Audio)

**Files:**
- Create: `frontend/lib/acoustics/player.ts`, `frontend/lib/hooks/useAcoustics.tsx` (provider + hook)
- Modify: `frontend/app/layout.tsx` (wrap in `AcousticsProvider`)

**Interfaces:**
- Produces: `useAcoustics()` → `{ play(name: "open"|"click"|"room-on"|"room-off"), muted, setMuted }`. Tones are synthesized on first user gesture (AudioContext resume); default unmuted but whisper-quiet (gain ≤ 0.08); **auto-muted when `prefers-reduced-motion: reduce`**; preference persisted.

- [ ] `player.ts`: lazily create `AudioContext`; `play(name)` maps to a short synthesized envelope (sine "open" chime ~2 notes; filtered-noise "click"; low sine "room" bed). Guard SSR (`typeof window`).
- [ ] `useAcoustics.tsx`: provider holds muted state (localStorage + reduced-motion), resumes context on first pointer/keydown; hook returns the API.
- [ ] Play `open` once on mount (post-gesture) — no autoplay violation.
- [ ] Commit `feat(frontend): whisper-quiet Web Audio acoustics with mute + reduced-motion`.

### Task 4: Motion + core surface primitives

**Files:**
- Create: `frontend/lib/motion.ts` (spring presets + reduced-motion helper), `frontend/components/primitives/{Surface,CarvedButton,Hairline}.tsx`

**Interfaces:**
- Consumes: tokens, `useAcoustics`.
- Produces: `<Surface raised? className>` (wakes on hover — subtle `--raised`/brightness spring), `<CarvedButton variant="default"|"brass" onClick>` (inner highlight + stroke, tactile press, plays `click`), `<Hairline>` (1px `--hairline` divider). `springs = { settle, wake, press }` and `useReducedMotionSafe()`.

- [ ] `motion.ts`: export spring presets; `useReducedMotionSafe()` wraps `useReducedMotion()` → returns instant transitions when reduced.
- [ ] `Surface`: `motion.div` with hover → `raised` background + 1px inner highlight; no shadow.
- [ ] `CarvedButton`: `motion.button`, `whileTap` scale 0.98 spring, inner-highlight + hairline stroke; brass variant uses `--brass` text/stroke; plays `click` on press.
- [ ] `Hairline`: presentational divider.
- [ ] Commit `feat(frontend): motion presets + Surface/CarvedButton/Hairline primitives`.

### Task 5: Conversation primitives — ThreadLine, EchoRail, Dock, CommandSurface

**Files:**
- Create: `frontend/components/primitives/{ThreadLine,EchoChip,EchoRail,Dock}.tsx`, `frontend/components/primitives/CommandSurface.tsx`

**Interfaces:**
- Consumes: Surface, CarvedButton, tokens, motion.
- Produces:
  - `<ThreadLine role="user"|"nova" timestamp? children>` — bubble-less; label + hairline + text; timestamp opacity-0 → hover.
  - `<EchoRail echoes: Echo[]>` where `Echo = { summary: string; when: string; created_at: string|null }` — dismissible tiny row under a nova turn; renders nothing if empty.
  - `<Dock items>` — floating nav; active item marked; disabled items (lens pages) dimmed + non-navigating with a "soon" title.
  - `<CommandSurface open onOpenChange onSubmit(kind,q)>` — ⌘K palette; `kind: "keyword"|"semantic"|"jump"`; keyboard-first; no thread pollution.

- [ ] Define `Echo` type in `frontend/lib/api/types.ts` (created here, extended in Task 6).
- [ ] `ThreadLine` + `EchoChip`/`EchoRail` (settle-in on mount; dismiss animates out).
- [ ] `Dock`: bottom-center floating; Desk/Chat active, lens routes dimmed.
- [ ] `CommandSurface`: global ⌘K listener, focus trap, segmented keyword/semantic, `Esc` closes.
- [ ] Commit `feat(frontend): ThreadLine, EchoRail, Dock, CommandSurface primitives`.

### Task 6: Typed API client + TanStack Query provider

**Files:**
- Create: `frontend/lib/api/types.ts` (extend), `frontend/lib/api/client.ts`, `frontend/components/QueryProvider.tsx`
- Modify: `frontend/app/layout.tsx` (wrap in `QueryProvider`)

**Interfaces:**
- Produces typed fns (all via `/api` same-origin):
  - `getHome(): Promise<HomeOut>` — `GET /api/home`
  - `getMessages(params:{limit?:number; before?:number}): Promise<MessageOut[]>` — `GET /api/messages`
  - `searchMessages(q,start?,end?): Promise<MessageOut[]>`, `searchMemory(q,limit?): Promise<MemoryOut[]>`
  - `postVoice(text,mode?,voiceId?): Promise<Blob>` — throws on non-200 (caller falls back to text)
  - `postChat(message,session_id?): Promise<ChatResponse>` — non-stream fallback
  - Types `HomeOut, MessageOut, Echo, MemoryOut, ChatResponse, ChatMeta, ChatTokenFrame` mirroring `docs/API_REFERENCE.md`.

- [ ] `types.ts`: transcribe response shapes exactly from API_REFERENCE (§ Conversation, Conversation log, Continuity).
- [ ] `client.ts`: a small `request()` wrapper (JSON, error→throw with `{status,detail}`); one fn per endpoint above.
- [ ] `QueryProvider`: `QueryClient` (staleTime 30s) + devtools in dev.
- [ ] Commit `feat(frontend): typed API client + React Query provider`.

### Task 7: Data hooks — useHome, useMessages, useVoice

**Files:**
- Create: `frontend/lib/hooks/{useHome,useMessages,useVoice}.ts`
- Test: `frontend/lib/hooks/__tests__/useMessages.merge.test.ts`

**Interfaces:**
- Consumes: client.
- Produces: `useHome()` (query); `useMessages()` → infinite query paging by `before=<top cursor>`, plus a pure exported helper `mergePages(pages: MessageOut[][]): MessageOut[]` returning oldest→newest deduped by `cursor`; `useVoice()` → `{ speak(text,mode), playing }` with 503→noop.

- [ ] **Write failing test** for `mergePages`: two overlapping newest-first pages → single ascending list, deduped by `cursor`.
- [ ] Run `npx vitest run useMessages.merge` → FAIL (not implemented).
- [ ] Implement `mergePages` + `useMessages` infinite query + `useHome` + `useVoice`.
- [ ] Run vitest → PASS.
- [ ] Commit `feat(frontend): home/messages/voice hooks + tested pagination merge`.

### Task 8: useChatStream (SSE reducer) — TDD

**Files:**
- Create: `frontend/lib/hooks/useChatStream.ts`, `frontend/lib/chat/streamReducer.ts`
- Test: `frontend/lib/chat/__tests__/streamReducer.test.ts`

**Interfaces:**
- Produces:
  - pure `streamReducer(state, frame)` where frames are `{type:"meta",data}|{type:"token",data}|{type:"done",data}|{type:"error",data}` and state = `{ phase:"idle"|"streaming"|"done"|"error"; text:string; meta?:ChatMeta; echoes:Echo[]; sessionId?:string }`.
  - `parseSSE(chunk, buffer)` → `{frames, buffer}` (splits on `\n\n`, parses `event:`/`data:`).
  - `useChatStream()` → `{ send(message,sessionId?), state, reset }`; on `error` frame or fetch failure, resolves by calling `postChat` and emitting a synthetic done.

- [ ] **Write failing tests:** (a) meta→token×3→done yields `phase==="done"`, `text` == concatenated tokens, `echoes` from done/meta; (b) `parseSSE` reassembles across a split chunk boundary; (c) `error` frame sets `phase==="error"`.
- [ ] Run `npx vitest run streamReducer` → FAIL.
- [ ] Implement `streamReducer` + `parseSSE`; then `useChatStream` (fetch `/api/chat/stream`, read `body.getReader()`, feed reducer; optimistic user turn handled by the page).
- [ ] Run vitest → PASS.
- [ ] Commit `feat(frontend): SSE useChatStream reducer with tested parsing + fallback`.

### Task 9: `/` The Threshold

**Files:**
- Create: `frontend/components/marketing/{Belief,HumanVerbs,BeginCTA}.tsx`
- Modify: `frontend/app/page.tsx`

**Interfaces:** Consumes primitives; no API.

- [ ] Compose: Fraunces belief statement, one human-verbs line, `Begin` CarvedButton → `/desk`; paper grain; one carved brass detail; generous silence; settle-in on load.
- [ ] Verify: renders both themes; no banned words; AA contrast.
- [ ] Commit `feat(frontend): the Threshold (/) marketing screen`.

### Task 10: `/desk` The Digital Desk

**Files:**
- Create: `frontend/components/desk/{GreetingBand,CurrentChapter,HeldThought,Weather}.tsx`
- Modify: `frontend/app/desk/page.tsx`

**Interfaces:** Consumes `useHome`, primitives.

- [ ] Render `HomeOut`: greeting (Fraunces), current chapter (or calm empty line), held thought (hidden if null), weather+stage+last-interaction ambient line, `Continue` → `/chat`.
- [ ] Empty state: `message_count === 0` → "This is where your life together will gather." Brass only if an earned milestone exists.
- [ ] Loading = calm settle (skeleton as faint hairline blocks, not spinners).
- [ ] Verify against live `/api/home`.
- [ ] Commit `feat(frontend): the Digital Desk (/desk)`.

### Task 11: `/chat` The Conversation

**Files:**
- Create: `frontend/components/chat/{MessageStream,Composer,VoiceButton,ChatSearch}.tsx`
- Modify: `frontend/app/chat/page.tsx`

**Interfaces:** Consumes `useMessages`, `useChatStream`, `useVoice`, `CommandSurface`, `ThreadLine`, `EchoRail`.

- [ ] `MessageStream`: history (oldest→newest, continue-from-bottom), "load older" by cursor; each nova turn renders `EchoRail`; streaming turn appends live text.
- [ ] `Composer`: textarea + send; optimistic user `ThreadLine`; disabled while streaming; Enter=send / Shift+Enter=newline.
- [ ] `VoiceButton` on nova turns → `useVoice.speak`; 503 stays silent-text.
- [ ] `ChatSearch`: ⌘K `CommandSurface` → keyword (`searchMessages`) + semantic (`searchMemory`); result jumps/scrolls thread; never renders in-thread.
- [ ] Empty state (day one): single invitation line; composer only.
- [ ] Verify full loop against live backend: send → tokens stream → echo appears (or none when guard true).
- [ ] Commit `feat(frontend): the Conversation (/chat) — history, streaming, echoes, voice, ⌘K search`.

### Task 12: Craft pass + dark-mode parity

**Files:** Modify primitives/screens as needed; `frontend/app/globals.css`.

- [ ] Tune springs (settle/wake/press) so nothing overshoots content; verify "arrives because ready" feel.
- [ ] Hover-wake on all Surfaces; grain only in ivory; obsidian sheen token in dark.
- [ ] Wire acoustics: open (mount), click (buttons), room bed (voice playback); mute control in Dock.
- [ ] Full dark-mode parity pass (contrast, brass, grain-off); reduced-motion pass.
- [ ] Commit `feat(frontend): craft pass — springs, hover-wake, acoustics, dark parity`.

### Task 13: Tests + Playwright smoke

**Files:**
- Create: `frontend/vitest.config.ts`, `frontend/vitest.setup.ts`, `frontend/playwright.config.ts`, `frontend/e2e/spine.spec.ts`
- Test: echo projection unit test `frontend/lib/api/__tests__/echoes.test.ts` (if a projection helper exists) — else covered by streamReducer.

**Interfaces:** none new.

- [ ] `vitest.config.ts` (jsdom, setup, `@` alias); `vitest.setup.ts` imports `@testing-library/jest-dom`.
- [ ] Ensure Tasks 7 & 8 unit tests run green: `npx vitest run`.
- [ ] `playwright.config.ts`: baseURL `localhost:3000`, `webServer` runs `npm run dev`, single chromium project.
- [ ] `e2e/spine.spec.ts`: `/` → Begin → `/desk` → Continue → `/chat` → type + send → assert streamed text appears and (echo rail present OR none when guard). Requires backend on `:8000`.
- [ ] Run `npx playwright test` (install browser once via `npx playwright install chromium`).
- [ ] Add `package.json` scripts: `"test": "vitest run"`, `"test:e2e": "playwright test"`.
- [ ] Commit `test(frontend): unit reducers + Playwright spine smoke`.

---

## Self-review notes

- **Spec coverage:** §1 soul → constraints + Task 9/11 copy; §2 decisions → Tasks 1–2; §3 layout → Task 1; §4 primitives → Tasks 4–5; §5 screens → Tasks 9–11; §6 data → Tasks 6–8; §7 errors/a11y → constraints + per-task verify + Task 12; §8 testing → Task 13; §9 sequence == task order; §10 out-of-scope → Dock dims lens routes (Task 5), no lens tasks. All covered.
- **Types:** `Echo`, `HomeOut`, `MessageOut`, `ChatMeta` defined in Task 5/6, consumed consistently in 7/8/10/11.
- **No font CDN / brass-earned / no-bubbles / graceful-degradation** enforced via Global Constraints on every task.
