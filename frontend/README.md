# Nova AI — Web App

Next.js 16 (App Router, Turbopack) · React 19 · Tailwind v4 · TanStack Query · motion · GSAP. Fifteen
routes, one permanent conversation and a set of lenses over the same data. Which screen uses which endpoint:
[`PRODUCT_SURFACE.md`](PRODUCT_SURFACE.md). Identity, voice and motion rules: [`BRAND.md`](BRAND.md).

## Run

Needs Node 20+ and the backend on `:8000` (see the [root README](../README.md#quick-start)).

```bash
npm install
npm run dev          # http://localhost:3000
```

`NEXT_PUBLIC_API_BASE` (default `http://127.0.0.1:8000`) points at the API. The first visit lands on `/welcome`.

### In Docker

```bash
# from the repo root; --no-deps leaves the running backend alone
docker compose -f docker/docker-compose.yml --profile app build frontend
docker compose -f docker/docker-compose.yml --profile app up -d --no-deps frontend   # http://127.0.0.1:3090
```

Run the same two commands after any frontend change to sync it into the container (the image is built from source, not mounted).

## Check

```bash
npx tsc --noEmit            # types
npm run lint                # eslint
npm test                    # vitest: copy tables, cursor physics, voice (61 tests)
npm run test:e2e            # Playwright against the running stack, including axe checks (95 tests)
```

Playwright needs the backend and its Postgres up. If the installed browser differs from the version
Playwright expects, set `PW_CHROMIUM=/path/to/chromium`.

## Layout

| Path | Holds |
|---|---|
| `app/` | One folder per route. `globals.css` holds the four light themes (dawn, day, dusk, night) as tokens, plus the fold, ruler and handwriting utilities. |
| `components/ui` | The design system: `Page`, `Sheet`, `Tabs`, `Button`, `States` (empty, loading, trouble), `Mark` (the stamp and its moods). |
| `components/brand` | Shared brand layer mounted by the shell: pen cursor, smooth scroll, margin notes (`Margin`), grain, motion helpers. |
| `components/shell`, `talk`, `memory`, `story`, `errands`, `goals`, `welcome` | Feature components. |
| `lib/` | API client and types, TanStack hooks, `voice.ts` (every line Nova says), `companion/` (mood, pointer lean), `cursor/` (pure cursor logic) and the plain-language mapping tables (`people.ts`, `goals.ts`, `care.ts`, `upkeep.ts`, `errands.ts`, `style.ts`, `time.ts`), each with a vitest file. |
| `e2e/` | Playwright specs: pages, navigation, accessibility in four lights, welcome scroll score, cursor, character. |
| `public/film/` | The rendered films for `/welcome`; source and render script in [`../film`](../film). |
