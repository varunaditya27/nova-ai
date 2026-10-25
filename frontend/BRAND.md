# Nova AI — Brand

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

## Personality: the keeper
Nova is a character, not a theme. It is **attentive** (notices the specific thing), **dry and warm** (one wry beat, never where someone is hurting), **honest about being unfinished**, and **brief**. It speaks in the first person wherever it is the speaker (pages, empty states, toasts, errors). The two exceptions are factual claims about data (`/privacy`, the `/welcome` explainers), which stay third-person so they read as promises, not chat.

| Layer | What it is | Where |
|---|---|---|
| **Voice** | All greetings, thinking lines, waiting lines, page notes, empty states and error lines live in one file with its rules written at the top. Lines rotate by day or message count, deterministically. | `lib/voice.ts` (tested) |
| **Body** | The stamp has no face; like a desk lamp in a short film it has character through movement. Moods: calm (breathes), thinking (pulses), happy (hops), sleepy (tilts, drifts a "z"), startled (jumps), lost (looks about). `alive` stamps lean toward your pointer and hop when you hover them. | `components/ui/Mark.tsx`, `lib/companion/` |
| **Habits** | After 90 quiet seconds the sidebar stamp dozes off and startles when you return; while a reply is being written every stamp on screen pulses together (`html[data-busy]`). Replies that just arrived press their stamp with a hop. | `lib/companion/mood.ts` |
| **Handwriting** | Margin notes in Caveat: Nova talking about its own page, tilted, with a pen-stroke that draws itself once. Optional reading only, never instructions. On inverted bands they take the ground colour for contrast. | `components/brand/Margin.tsx` |
| **Everywhere** | Every inner page carries a note (`Page note=`); every empty state is an `<Empty kind=...>` with its own line; loading shows what Nova is doing (and changes the line if the wait is long); errors are calm, take the blame, and the stamp looks lost; toasts carry a hopping stamp; the 404, error page, command menu, nav captions, sheets, upkeep chores and care page all speak in the voice. | `components/ui/`, `app/` |

Rules: no jokes in errors, the Care page, or crisis replies. A new surface isn't done until it has a line in `lib/voice.ts` or an existing pattern that gives it one.

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
