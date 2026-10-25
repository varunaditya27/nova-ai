# Nova web app

Next.js 16 (App Router, Turbopack) · React 19 · Tailwind v4 · TanStack Query · motion. The screens and
the endpoints behind each are in [`PRODUCT_SURFACE.md`](PRODUCT_SURFACE.md).

## Run

```bash
# backend on :8000 first (see the root README), then:
npm install
npm run dev          # http://localhost:3000
```

`NEXT_PUBLIC_API_BASE` (default `http://127.0.0.1:8000`) points at the API.

## Check

```bash
npx tsc --noEmit            # types
npm run lint                # eslint
npm test                    # vitest (unit)
npm run test:e2e            # Playwright against the running stack, incl. axe accessibility checks
```

Playwright needs the backend and a Postgres-backed database up. If the installed browser differs from
Playwright's expected version, set `PW_CHROMIUM=/path/to/chromium`.

## Layout

- `app/` — one folder per route; `globals.css` holds the four light themes as tokens.
- `components/ui` (Page, Sheet, Tabs, States, Ember), `shell` (nav, command menu), `talk`, `memory`,
  `story`, `errands` — feature components.
- `lib/` — API client + types, TanStack hooks, and the plain-language mapping tables (`people.ts`,
  `goals.ts`, `care.ts`, `upkeep.ts`, `errands.ts`, `style.ts`, `time.ts`), each with a vitest file.
- `e2e/` — Playwright specs.
