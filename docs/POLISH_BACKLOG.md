# Polish Backlog

Running log of follow-up work surfaced while auditing each layer, one phase at a time (see
CLAUDE.md's "Polish phases" pointer). Each phase reads its layer's code end-to-end, verifies it
does what its architecture doc says, removes dead/bloated code, fixes what's cheaply fixable, and
logs the rest here instead of fixing it on the spot — scope creep between layers is exactly what
this file exists to prevent.

Entries are grouped by the layer that surfaced them. Mark an entry `[done]` with the commit/PR
that closed it instead of deleting the entry — it's the record of what got skipped and why.

---

## Layer 1 — Input Perception (audited 2026-08-04)

Module (`backend/layer1_input/`) itself had no dead code or bloat — every symbol has a caller.
The findings below are gaps between what the module can do and what the live pipeline actually
feeds it. Full detail: `docs/layer-1-architecture.md` §16.

- **Narrative-thread creation.** Nothing anywhere constructs a `NarrativeThread` — `due_threads`
  is always `[]` live, and `backend/layer6_proactivity/intake.py::on_thread_due` is an orphaned
  consumer waiting for input that never arrives. Needs a detector (likely LLM-based) that spots
  open loops in conversation ("I have a job interview Thursday", "I'll call my mom back") and a
  persisted `ThreadStore`. This is a real feature to design, not a wiring fix.
- **Implicit signals + multimodal/voice never fire live.** `ChatRequest` (`api/schemas.py`)
  carries only `message` + `session_id` — no typing-start timestamp, deletion count, burst info,
  or attachments. So SC-2 (implicit signal extractor) always scores a fixed low intensity, and
  SC-3/SC-4 (multimodal normalizer, voice prosody) never fire — attachments are hardcoded to `[]`
  in `api/assembly.py::perceive`. Fixing this needs a `ChatRequest` schema change (additive,
  optional fields) plus frontend instrumentation to actually populate them — a coordinated
  backend+frontend change, not backend-only.
- **`config/layerN.yaml` files are unread.** Fixed the *loading* gap this phase (all 13 now merge
  into the config dict via `api/state.py::build_app_state`). Still open: no layer module actually
  reads `config['layerN']` — every threshold (circadian bands, gap buckets, intensity weights,
  etc.) is a hardcoded Python constant. Realizing the YAML's stated purpose ("re-tune without a
  code change") means threading config through each layer's functions — do this per-layer as each
  is revisited, not as one big cross-cutting change.
- **Circadian histogram is UTC-based.** `make_temporal_profile_provider`'s `typical_bands`
  bucketing uses the stored (UTC) hour, matching `timezone_offset_hours` always defaulting to
  `0.0` (never populated anywhere). Currently consistent because both sides are UTC. The moment
  something starts capturing a real user timezone, this derivation needs the same offset applied,
  or the live band and the historical histogram will silently diverge.

---

<!-- Next phase (Layer 2 — Memory) appends its section below this line. -->
