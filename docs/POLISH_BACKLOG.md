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

## Layer 2 — Cognition & Memory (audited 2026-08-04)

Same shape as Layer 1: every module has a real caller (production or its own tested public API),
no unreachable code. But five of the eight sub-components are complete and tested in isolation
with **zero live production callers** — bigger in aggregate than Layer 1's gaps, because each one
needs a new detector, table, or LLM step rather than a small adapter. Full detail:
`docs/layer-2-architecture.md` §20.

- **User World Model is never created for any real user.** `UserWorldModel(` is constructed only
  in tests. `state_updater`'s UWM step only bumps `update_version` on an *existing* row — nothing
  creates the first one — so `store.load_uwm(user_id)` always returns `None` live, which means
  `arbiter._attach_uwm` always sets `uwm_unavailable=True` and `uwm_context` is always the empty
  default. The entire profile/relationship-graph/life-context/psychological-model/communication-
  model structure (`schemas.py`, ~160 lines) is unused live. Needs a real extraction+merge step
  (an "UWM updater," referenced by `state_updater`'s own comment but not implemented) that reads
  the turn and updates these fields — a substantial feature, likely LLM-assisted, not a wiring fix.
- **Identity Memory is never seeded or updated.** `IdentityMemory(` is constructed only in tests;
  `apply_identity_update` (contradiction-driven belief revision, the resistance-scales-with-
  centrality mechanism) has zero live callers because nothing ever creates an `IdentityContradiction`
  to feed it. Nova has no live self-model — `identity_beliefs()` always returns `[]`. Needs (a) an
  initial seed of core beliefs/values (`scripts/seed_db.py` doesn't touch identity) and (b) a
  contradiction-detection mechanism, which doesn't exist anywhere in the codebase.
- **Narrative-chain linking (SC-8, distinct from Layer 1's narrative *threads*) is orphaned.**
  `detect_narrative_links` is fully implemented and tested but has zero live callers, and there's
  no persisted `NarrativeChain` table (`infra/db/models/memory.py` has no such model) — so
  `active_narrative_chains` is always `[]`/`None` live. Needs a store + a call site in the
  post-turn write path.
- **Episodic memory extraction is a stub, not the LLM summarization it's typed as.**
  `state_updater.py`'s `EpisodeExtractor` type alias says "Production wires the Episodic Memory
  Extractor (LLM summarization)"; the actual production extractor in `api/state.py::
  make_state_update_writer` is `message[:2000]` — a raw truncation of the current message, one
  episode per turn, no summarization, no multi-turn synthesis. Works well enough for the recall
  loop to function end-to-end (confirmed live), but doesn't match what the type alias promises.
- **STM buffer (SC-1) is never actually accumulated.** `stm.add_turn`/`should_promote` (eviction +
  promotion-to-episodic logic) are tested but have zero live callers — `api/state.py`'s writer
  constructs a fresh, empty `ShortTermMemoryBuffer` every single turn and the extractor closure
  ignores it entirely. The promotion-on-eviction mechanism (high-arousal or life-event-keyword
  turns get promoted to episodic memory even if never explicitly summarized) never runs.
- **Recall's `conversation_mode` is always `default_mode`, not the real one — by design, not a
  gap.** Recall runs before Layer 3 classification (`docs/NOVA_AI_MASTER_ARCHITECTURE.md` §3 steps
  3 vs 5), so there's no mode signal available yet. Documented in §11.2's as-built note; nothing to
  fix here.

---

<!-- Next phase (Layer 3 — Reasoning) appends its section below this line. -->
