# Nova AI — Documentation

Where things are written down, and how to read them. When code and a document disagree, **the code is
right**; fix the document in the same change.

## Reading order

| Read | For |
|---|---|
| [`../README.md`](../README.md) | What Nova is, how to run it, what is real and what is not yet |
| [`NOVA_AI_MASTER_ARCHITECTURE.md`](NOVA_AI_MASTER_ARCHITECTURE.md) | The canonical map: one conversation turn, the 13 layers, invariants, storage, infrastructure |
| `layer-N-architecture.md` | The deep spec for one layer, ending in an **as-built** section and a dated decision log |
| [`API_REFERENCE.md`](API_REFERENCE.md) | Every HTTP endpoint and schema (live schema at `GET /openapi.json`) |
| [`../frontend/BRAND.md`](../frontend/BRAND.md) | The web app's identity, voice and motion rules |
| [`../frontend/PRODUCT_SURFACE.md`](../frontend/PRODUCT_SURFACE.md) | Which screen uses which endpoint |
| [`../film/README.md`](../film/README.md) | Rendering the landing-page films |
| [`POLISH_BACKLOG.md`](POLISH_BACKLOG.md) | The running log of everything found while auditing, done and open |
| [`PENDING_WORK.md`](PENDING_WORK.md) | The same log filtered to what is still open |
| `superpowers/` | Dated design specs and implementation plans. A historical record: they describe what was decided then, not necessarily what exists now |
| [`../CLAUDE.md`](../CLAUDE.md) | Working agreement for contributors and coding agents |

## Layer names

The same name is used in every document, heading and table.

| # | Name | # | Name |
|---|---|---|---|
| 1 | Input Perception | 8 | Tools & Actions |
| 2 | Memory | 9 | Output & Interaction |
| 3 | Emotion & Reasoning | 10 | Longitudinal Life |
| 4 | Persona & Generation | 11 | Safety & Crisis |
| 5 | Social Intelligence | 12 | Privacy & Data |
| 6 | Proactive Engagement | 13 | Onboarding & Cold Start |
| 7 | Goals & Accountability | | |

## Writing style

One style across every document.

- **Titles:** `# Nova AI — Subject` for top-level documents, `# Layer N — Name` for layer specs. Sentence case
  for every heading below that. No emoji, no decorative glyphs.
- **Open with the point.** One or two sentences saying what the document is for, then the content.
- **Say what is real.** Mark anything not yet built or not yet deployed plainly ("designed, not deployed"),
  and link to the backlog entry. Never describe a plan in the present tense.
- **Plain, specific, short.** Prefer a table or a list to a paragraph of adjectives; prefer a number to
  "many". Define a term once, in the master architecture.
- **Dates and decisions.** Decisions are logged with an ISO date (`2026-10-25`) in the layer's decision log
  and in the backlog; the backlog entry is marked `[done]` when closed.
- **Code and paths in backticks;** commands in fenced blocks with the language named.
- **Diagrams** are hand-authored SVG in `docs/diagrams/`, in the brand palette, with a caption that states
  what the picture shows and alt text that says the same.
- **Voice:** documentation is neutral third person ("Nova remembers…"). Only the product itself speaks as
  Nova in the first person; its rules are in `frontend/BRAND.md`.
