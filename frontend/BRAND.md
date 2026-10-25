# Nova — brand

## Product truth
Nova is a companion that **keeps** things: what you said, what mattered, how you've changed. It is not a chatbot and not an assistant. The identity has to feel like something kept over years — a journal, an archive — and never like a gadget.

Attributes: **kept · warm · unhurried · private · earned.**

## The idea: "kept"
Everything visual comes from the physical journal: a stamp pressed on a page, a folded corner marking your place, a ruler of growth marks, a pen.

| Element | Where | Rule |
|---|---|---|
| **Stamp** (`components/ui/Mark.tsx`) | Logo, favicon, Nova's reply avatar, empty states, films | A bookplate square with a dog-eared corner and an italic "n". `Lockup` = stamp + wordmark. |
| **Dog-ear** (`.fold`, `.fold-sm`, `.fold-lg`) | Buttons, cards, fields, the stamp | The only signature shape. Never on nav items, list rows, segments or anything tiny. |
| **Ruler** (`.ruler`, `Meter`) | Progress, strength, depth | Growth is shown as marks on a ruler, never a glossy bar. |
| **Pen cursor** (`components/brand/NovaCursor.tsx`) | Whole app on fine pointers | Ink dot, lagging ring, ink trail. Brackets close on clickable things, a bar on text, a slash when blocked, handwriting while Nova writes (`html[data-busy]`). Can be switched off in the sidebar. |
| **Type** | — | Libre Baskerville 700 for display, Literata for reading, IBM Plex Mono for labels and timestamps (`.label`, `.stamp-text`). |
| **Colour** | `globals.css` `[data-light]` | Maroon `#800000`, teal `#006680`, green `#006600`, amber for "earned", on warm paper `#faf7f5` / `#1c1917`. Dawn and dusk are derived. The light follows the user's real hour. |
| **Motion** | `lib/motion.ts`, GSAP | "Premium": no overshoot, ease `[0.16,1,0.3,1]`, durations .35 / .5 / .8 s, entrances pull focus (rise + unblur). Everything has a reduced-motion tier. |

## Rejected, and why
- **Star / spark / sparkle** — the default AI mark; says "magic", not "kept".
- **Orb / blob / aurora** — same; and it carries no information.
- **Spiral / thread** — pretty, but it was decoration with no product meaning.
- **Chat bubbles with tails** — Nova is a thread you keep, not a messenger.
- **Pill buttons** — the most recognisable generic-UI tell. Rectangles with one folded corner instead.
- **Poppins** — from the supplied theme; geometric sans reads as SaaS. The palette was kept, the type was not.

## Rules of thumb
1. If a new element needs decoration, ask which journal object it is. If none, leave it plain.
2. One signature shape, used sparingly, beats five used everywhere.
3. Plain language only. No enum values, ISO dates or decimals reach the screen.
