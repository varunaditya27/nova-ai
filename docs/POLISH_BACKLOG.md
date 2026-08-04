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

## Layer 3 — Emotion, Intent & Reasoning (audited 2026-08-04)

Two critical safety/routing bugs found and **fixed** this phase (attribute-name mismatches
invisible to the test suite because every orchestrator test mocks `classify`) — see
`docs/layer-3-architecture.md` §17 for full detail. This layer had far less "complete but
unwired" scaffolding than Layers 1-2; most of what's left is smaller connection gaps.

- **`alert_fn` (async CrisisAlert push to Layer 11) is never wired.** Not a safety gap — the
  orchestrator reads `crisis_active` directly off the returned packet and ORs it with Layer 11's
  independent scan — but the specific "immediate, before-the-packet-completes" notification
  behavior the doc describes doesn't happen. Would need `api/assembly.py` to pass a real
  `alert_fn` that forwards into whatever Layer 11 uses to receive early signals (check whether
  Layer 11's `evaluate()` even has a push-receiving counterpart, or whether this is redundant
  with SC-2's own scan and not worth wiring at all).
- **SC-1 and SC-3 each call `llm_fn` separately** — two LLM calls per turn, not the single shared
  small-model call §14.2 describes. Not a correctness bug (both calls work), but a latency/cost
  gap relative to the documented design. Would need `packet_builder.py` restructured so one LLM
  response feeds both classifiers.
- **BES (Background Emotional State) inputs are never forwarded.** `episodic_memories`,
  `active_stressors`, `psychological_model` all default to empty/`None` in
  `api/assembly.py::classify` — consistent with Layer 2's finding that the User World Model and
  real episodic-memory querying are inert live, so there's nothing real to forward yet. Closes
  automatically once Layer 2's UWM gap does.
- **`relationship_depth` and `advice_frustration_count` are never forwarded**, despite
  `PostgresRelationshipStore` (Layer 4/5) having real session/message counts that could derive a
  `relationship_depth` proxy today (`relationship_provider` already exists — this is a small
  adapter, similar in shape to Layer 1's temporal-profile fix).
- **`composite_prior`'s prior-adjustment branch is forwarded but still unreachable.** Verified
  directly: with Layer 1's `implicit_intensity` pinned at 0.10, `composite_prior` cannot exceed
  ~0.39, below `integrate_prior`'s `> 0.6` gate. Reopens once Layer 1's implicit-signal gap
  (`ChatRequest` client-behavioral-data gap, above) closes — no Layer 3 code change needed then.

---

## Layer 4 — Persona, Personality & Response Generation (audited 2026-08-04)

The module itself (`backend/layer4_persona/`) is clean — 81 tests, no dead code, every
sub-component matches its architecture-doc reconciliation notes. The finding is structural: the
real orchestrator (`packet_builder.build_final_response_packet`, SC-1 through SC-6) has **zero
production callers** — `api/assembly.py` runs a separate, much thinner hand-built path. Four small
signal-forwarding gaps in that path were fixed this phase (recalled memories, advice gate,
circadian band, a raw-score-leak field-name bug in `_format_memories`) — see
`docs/layer-4-architecture.md` §16 for full detail. What's left is real feature work, not wiring:

- **`refine()` doesn't call the real `emotion_refiner.refine_emotion`.** `api/assembly.py`'s
  `refine()` sends a fixed ad hoc prompt to the LLM instead of the tested SC-6 implementation —
  no five-condition skip policy, no factual-preservation validation/reinsertion, no voice
  parameters or empathy hypothesis threaded in. Not a drop-in fix: the orchestrator
  (`conversation_orchestrator.py`) sets `ctx.refined = True` unconditionally whenever `refine()`
  runs at all, so wiring the real skip policy would make that field a lie without also touching
  the orchestrator's contract — and the Phase-3 regression test asserts `out.refined is True`.
  Needs a coordinated change across `conversation_orchestrator.py` and `api/assembly.py`, not a
  same-shape adapter fix.
- **SC-1 (persona_resolver), SC-3 (tone_calibrator), SC-4 (drift_detector) never run live.**
  `build_persona()` hand-assembles a `PersonaPacket()` missing `persona_state`,
  `voice_parameters`, and `drift_check_result` entirely. This is an identity-consistency gap, not
  a safety hole (Layer 11 SC-1 Ethical Guardrails still runs post-generation on every response),
  but the four §11 "identity under pressure" rules — no capitulation to social pressure, no
  claimed qualia, no validating harmful beliefs, no abandoning character on request — do not fire
  pre-generation as designed. SC-3 wiring is coupled to this: voice parameters are inert until
  SC-5/SC-6 are updated to consume them, so this and the `refine()` item above should land
  together.
- **`build_final_response_packet` wiring collides with System 1/2 routing.** The orchestrator's
  `_run_system1`/`_run_system2` hooks decide whether the Emotion Refiner runs at all (System 1
  skips it structurally); `build_final_response_packet` makes that same decision internally via
  the five-condition skip policy. Wiring the real orchestrator wholesale means deciding which of
  the two owns that decision — a design question to resolve before implementing, not a wiring fix.
- **`RelationshipState.compute_relationship_state`'s style-calibration overwrite is a latent
  trap.** `_apply_style_calibration` unconditionally overwrites the four EMA-learned
  communication-style params (`response_length_preference`, etc.) from a coarse one-shot
  `communication_model` derivation whenever a `communication_model` is passed in. Currently inert
  live because Layer 2's UWM is never populated (`communication_model` is always `None` — see the
  Layer 2 entry above), but whoever eventually wires SC-2 into the live path needs to either drop
  this overwrite or make it additive, or it will silently discard the learned EMA values from
  `style_learning.py` every turn.

---

<!-- Next phase (Layer 5 — Relationship) appends its section below this line. -->
