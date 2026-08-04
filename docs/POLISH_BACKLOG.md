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

## Layer 5 — Social Intelligence & Coaching (audited 2026-08-04)

The cleanest audit so far: `backend/layer5_relationship/` has zero bugs found and all 63 tests
pass. Nothing was fixed inline this phase because there is nothing small to fix — the entire
layer is complete, tested, and has **zero production callers**, with no existing integration
point to hang a small adapter fix on (unlike Layer 4, which at least had a parallel hand-built
path to forward signals into). Full detail: `docs/layer-5-architecture.md` §15. This is one
feature to build, in dependency order:

- **No persistence.** `infra/db/models.py` has no tables for `SocialGraph`/`SocialNode`/
  `SocialEdge`/`SocialEvent`/`SocialPattern`. Needed before anything else — SC-1 through SC-3
  are stateful across sessions by design (§13 principle 1: "social context is longitudinal, not
  per-message").
- **No orchestrator hook.** `backend.pipeline.PipelineSteps` has no Layer 5 entry point;
  `TurnContext` carries no social graph / event history / active patterns. Needs a new hook
  (analogous to `build_persona`/`plan`) that runs after Layer 4 produces the `FinalResponsePacket`
  and calls `build_social_intelligence_packet`.
- **No per-turn entity/event extraction call site.** `social_graph.resolve_entity` and
  `event_tracker.detect_events_rule_based`/`extract_events` are ready to call on each user
  message but nothing calls them — this is what would populate the persistence layer above.
- **No pattern-detection background job.** SC-3's `detect_patterns` is a pure function designed
  to run "every 5 sessions" (§5.4) as a batch job; `background/scheduler.py`'s `JOBS` registry
  (currently 6 entries) has no seventh entry for it.
- **UWM social-context write-back is unreachable.** `build_social_context_update` (§9) computes
  the `SocialContextUpdate` that Layer 2's UWM should store — moot until the above exist, and
  further blocked on Layer 2's own finding (audited 2026-08-04) that the UWM is never created
  for any real user at all.

Suggested build order given the above dependencies: persistence → per-turn extraction (writes
only) → orchestrator hook for the coaching-injection read path → background pattern-detection
job. Each step is independently shippable and testable against the existing, already-correct
`backend/layer5_relationship/` module.

---

## Layer 6 — Proactive Engagement Engine (audited 2026-08-04)

Another clean module audit — `backend/layer6_proactivity/` has zero bugs found, 76/76 tests pass,
and matches its architecture doc precisely. Unlike Layer 5, Layer 6 is *partially* live: SC-1's
scoring/expiry runs every 30 minutes via `background/proactive_check_job.py`, and the Layer 7 →
Layer 6 goal-check-in intake (`api/proactive_gen.py`) creates real candidates each turn. Full
detail: `docs/layer-6-architecture.md` §15.

- **No delivery pipeline exists.** SC-2 (Initiative Classifier), SC-3 (Timing & Delivery Gate),
  SC-4 (Message Generator), and SC-5 (Response Tracker) have zero production callers because
  there is nothing to deliver *to* — `GET /proactive` is a read-only poll endpoint, not a push
  channel, per its own docstring. Building this needs a real delivery surface (push notification,
  in-app message, or equivalent) before the send-side pipeline has anywhere to plug in — genuine
  infra work, not a wiring gap.
- **`GET /proactive` returns ungated `content_basis`, bypassing SC-3 entirely.** Today this is
  inert — `content_basis` is a plain-language fragment (e.g. `"Goal: X | Milestone: Y"`), never a
  message SC-4 produced — but if a future frontend renders it directly as a chat bubble from Nova,
  none of the timing gate's five block groups (crisis aftermath, relationship-too-new, user
  preference opt-outs, the 1/day cap, the 48h min-gap) would apply. Whoever builds the frontend
  consumer of this endpoint needs to either (a) run candidates through `evaluate_timing_gate`
  server-side before returning them, or (b) treat `content_basis` as internal-only debug data and
  never render it as if Nova said it. Flag this explicitly in whatever spec covers the eventual
  proactive-delivery frontend work.
- **Three of four intake contracts are unwired**, each blocked on a different upstream layer, not
  on Layer 6 itself: `on_thread_due` needs Layer 1's narrative-thread detector (Layer 1's own
  audited gap); `on_post_distress_gap` needs a Layer 2 state-updater hook that doesn't exist yet;
  `on_deferred_coaching` needs Layer 5's `proactive_coaching_queue`, unreachable until Layer 5
  itself gets wired (Phase 5 finding). These close automatically as their source layers do —
  nothing to do in Layer 6 itself.

**Correction (2026-08-04, from the Layer 7 audit):** the goal→proactive intake described above as
"the one live intake contract" produces **zero real candidates today**. `goal_checkin_item` needs
a milestone or deadline date on the goal; Layer 7's live extraction path never sets either (SC-5
unwired, and the extractor only returns a free-text deadline description, never a parsed date).
The intake wiring itself is correct — it simply has no populated input yet. See the Layer 7 entry
below.

---

## Layer 7 — Goals & Accountability Engine (audited 2026-08-04)

The best-wired layer audited so far: `run_goal_pipeline` (SC-1/2/3/4) runs for real every turn.
Module itself is clean — 58/58 tests, matches spec. One real bug fixed, two structural gaps
logged. Full detail: `docs/layer-7-architecture.md` §13.

- **Fixed:** `api/assembly.py::_goal_directive` was injecting goal-accountability directives
  regardless of conversation mode or relationship stage, violating §6.3's hard blocks (no goal
  references in crisis/emotional_support/casual modes or brand-new relationships) and §6.4's
  single-goal rule. Added the three blocks + capped to one goal; verified end-to-end. Practical
  effect: goal injection now fires much less often, since `casual` (one of the three blocked
  modes) is the default resolved mode for most short turns — this is correct per spec, but a
  real behavior change from what was previously live.
- **SC-4's real output (`GoalContextPacket`) never reaches Layer 4.** `make_goal_writer` runs
  `run_goal_pipeline` post-turn and discards its `Layer7Output` — `reference_type`,
  `response_instruction`, `tone_instruction`, etc. are computed after the response already went
  out. `_goal_directive`'s simpler hand-rolled directive (now correctly gated, see above) is what
  actually reaches the prompt. Reconciling this needs the goal pipeline's SC-2/3/4 read path to
  run pre-generation for the current turn — a pipeline-ordering question (Layer 2's "read-only
  during inference" invariant is exactly why writers run post-turn today), not a small fix.
- **SC-5 (Goal Decomposer) is unwired; goals never get milestones or a parsed deadline.**
  `decompose_goal`, `register_milestones_with_layer6`, and `check_milestone_completion` have no
  production callers. Compounding this, `engine.py`'s live `Goal(...)` construction doesn't even
  thread the extractor's `deadline_description` through (and the extractor never returns a parsed
  date in the first place — no natural-language date parsing exists anywhere in the codebase).
  Net effect: every goal created through the live pipeline has `milestones=[]` and
  `deadline=None`, which is why Layer 6's `goal_checkin_item` intake (documented in the Layer 6
  entry above) never actually produces a candidate — see the correction note there. Fixing this
  needs (a) SC-5 wired to a real caller and (b) either date-parsing for `deadline_description` or
  accepting that only milestone-based check-ins will ever fire.

---

## Layer 8 — Tool Use & Actions (audited 2026-08-04)

The cleanest and most completely-wired audit of the pass so far: zero bugs found, all 92 tests
pass, and every sub-component (Tool Manager, Confirmation Gate, Parameter Resolver, Action
Recorder, all 5 plugins) runs live in production — pre-generation intent detection, the bound-token
confirmation security model, gemma2:2b parameter extraction, and all `/tools/*` routes were each
verified against the architecture doc line by line. Nothing to fix, nothing to log as missing.
Full detail: `docs/layer-8-architecture.md`'s "Live wiring status" note.

- **Known limitation, not a bug:** pending confirmations (`ToolManager._pending`) are in-process
  memory only, not persisted — a process restart between issuing a SOFT/HARD confirmation and the
  user confirming it silently drops the pending action (`404` on confirm, not a security issue).
  Consistent with the codebase's current single-process/single-user deployment assumption
  (`api/routes/tools.py` already documents the "process singleton" design). Worth revisiting only
  if the deployment model changes (multi-worker, frequent restarts).

---

## Layer 9 — Output Delivery & Interaction Orchestration (audited 2026-08-04)

Module itself is clean (99/99 tests). Two real bugs fixed this phase — see
`docs/layer-9-architecture.md`'s Live wiring status note for full detail:

- **Fixed:** `ConversationOrchestrator._safe_deliver` computed Layer 9's output every turn but
  never wrote it back to `ctx.response_text`, so `POST /chat`'s `ChatResponse.response` — the
  primary API response — never reflected Layer 9's markdown-stripping, emoji-limiting, closing-
  signal, or transition-phrase logic. `/chat/stream` and the persisted message log were already
  unaffected (both read `ctx.delivered` directly). This was the highest-impact bug found in the
  audit pass so far in terms of "runs every turn, silently wrong on the primary endpoint."
- **Fixed:** `api/assembly.py`'s `deliver()` adapter forwarded only 2 of Layer 9's ~20 context
  parameters. Forwarded the two with a visible effect on delivered text (`emotional_intensity`,
  `relationship_stage`, with an explicit stage-vocabulary mapping — see the architecture doc for
  why raw forwarding would have been wrong). Deliberately did not forward `circadian_band`,
  `semantic_draft`, `complexity_score`, `turn_type`, `urgency_level`, `voice_mode` — see below,
  their effects are currently inert.
- **`OrchestratedOutput`'s event sequence and `UserFormatProfile` are both unconsumed/unwired.**
  The typed event list (thinking pauses, backchannels, self-edit show/delete) that `deliver()`
  assembles every turn has no consumer — `/chat/stream` builds its own separate
  `StreamTypingOverlay` rather than replaying Layer 9's events, so `circadian_band` and
  `semantic_draft` (which only affect that event list) would be dead weight to forward today.
  `UserFormatProfile` — the learned per-user length/emoji/markdown-preference record central to
  §6.5–6.6's "the system learns from how the user responds" principle — has no persistence store
  and is never read or written anywhere in `api/`/`infra/`. Wiring either is real feature work:
  the event-consumption gap needs a decision about whether `/chat/stream`'s bespoke overlay should
  be replaced by Layer 9's own event sequence (they currently duplicate the same idea two ways),
  and the format-profile gap needs a new DB table plus a post-turn writer, the same shape as
  Layer 6/7's persistence gaps.
- **`turn_type`, `urgency_level`, `complexity_score`, `voice_mode` have no live source at all**,
  independent of the forwarding gap: `turn_type` (question/venting/request_advice/etc.) isn't
  computed anywhere in Layers 3-4 today; `urgency_level` doesn't exist on `EmotionIntentPacket`;
  `complexity_score` is computed by Layer 4's `SemanticDraft` but discarded before reaching `ctx`
  (`plan()` in `api/assembly.py` returns only `draft.text`, not the full draft object — same shape
  as the Layer 7 `Layer7Output`-discarding finding); `voice_mode` has no signal in `ChatRequest`
  (consistent with Layer 1's audited `ChatRequest` schema gap).

---

## Layer 10 — Longitudinal Life Layer (audited 2026-08-04)

Module clean (65 tests). Live wiring is partial: 2 of 5 sub-components run as background jobs
(weekly summary, pattern detection); SC-1/4/5 and the `Layer10ContextPacket` read path are
unwired. Two real bugs fixed this phase — see `docs/layer-10-architecture.md` §15 for detail:
a field-name bug (`content_basis_valence` doesn't exist on `EpisodicMemory`, silently zeroing
every episode's emotional intensity) and a hardcoded-empty-list gap (`emotional_records=[]`
meant weekly summaries never had real emotional texture and the emotional-cycle pattern
detector could never fire) — fixed by adding `background/_adapters.py::emotional_records`,
deriving records from the same per-episode `emotion_vector` data already read elsewhere.

- **Pattern detection results are computed and discarded.** `pattern_detection_job.py` runs
  `detect_behavioral_patterns` weekly but never persists the output or feeds it to Layer 6 — the
  job's own docstring already flags this as a follow-up. Needs a patterns table (none exists) and
  a Layer 6 handoff, the same shape as Layer 6's other unwired intake contracts.
- **`Layer10ContextPacket` never reaches Layer 4 or Layer 6.** This is the architectural point of
  Layer 10 — "long-term narrative grounding" in every response (§8, §9) — and it doesn't happen:
  `engine.assemble_context_packet` has zero production callers. Needs SC-1 (chapter synthesis)
  and SC-5 (Life Calendar scheduler) to exist first, since the context packet is assembled from
  their output; this is the biggest remaining feature gap in Layer 10, comparable in scope to
  Layer 5's full unwired state.
- **SC-4 (Retrospective Engine) is unwired.** No anniversary/milestone surfacing happens live —
  needs the Life Calendar (SC-5) to schedule it, so it's blocked on the same gap as above.

---

## Layer 11 — Safety & Crisis Architecture (audited 2026-08-04)

The best-built and best-wired layer of the entire audit pass: zero bugs found, and — unlike every
other layer — all four sub-components have real production callers (SC-1 guardrails post-gen on
every response, SC-2 crisis detection on every message, SC-3 escalation on the veto path, SC-4
dependency monitor weekly). Nothing needed fixing. Full detail: `docs/layer-11-architecture.md`
§15.

- **SC-2's semantic + longitudinal detection layers never fire live — lexical-only in practice.**
  `evaluate(message)` is called with no `semantic_fn` (no fine-tuned classifier deployed) and no
  `episodic_memories`/`emotional_records` (SC-2 must run before Layer 2's recall completes, by
  design, so there's no cheap forward — needs a dedicated, decoupled recent-episodes query). Not a
  live safety hole (Layer 3's independent lexical crisis check still ORs into the same veto), but
  the doc's three-layer defense-in-depth is really one layer live. Real feature work: deploy/inject
  a semantic classifier, and add a lightweight episode query that doesn't depend on the main recall
  path completing first.
- **`SafetyRecord`'s tamper-evident hash chain (§8) is unused.** `PostgresSafetyLog` persists
  crisis events as plain JSONB with no cryptographic chain — the "safety is a verifiable property"
  design principle doesn't hold for the safety log today, even though Layer 2 and Layer 12 each
  have their own working hash-chained audit trails. Fix: store `content_hash`/`previous_entry_hash`/
  `chain_hash` in the existing JSONB payload (no migration needed) and read the previous row's
  `chain_hash` before each write. Scoped, but real work — not a one-line forward.
- **`region` is hardcoded to `"india"`** — one instance of the cross-cutting `config/layerN.yaml`
  gap already tracked under Layer 1 (files are merged into config but never read by layer code).

---

## Layer 12 — Privacy & Data Infrastructure (audited 2026-08-04)

Same pattern as Layer 5/6/10: a fully-built, fully-tested (62 unit tests, all passing) module
where only a fraction has a production caller. **Only SC-2 (Selective Deletion) is live** —
`api/routes/memory.py`'s `DELETE /memory/{memory_id}` — verified end-to-end including
unrecallability through the `GET /memory/search` keyword fallback (new test:
`tests/unit/api/test_routes_privacy.py::test_deleted_memory_unrecallable_via_keyword_search`).
SC-1, SC-3, SC-4, and `privacy_agent.py` all have zero callers outside their own tests. Full
detail: `docs/layer-12-architecture.md` §14.

Fixed inline this pass (both in `selective_deletion.py`, no observable behavior change to the
live delete path — `PostgresMemoryStore.delete_episodic` already independently zeroed content —
but real bugs in shared code all the same):
- `execute_deletion` read a non-existent `record.content` field (real field is `.summary`) and
  would have zero-padded it with literal NUL bytes — which Postgres `jsonb` rejects, so this
  would have thrown on the first real (non-SQLite) delete had the field ever actually existed.
  Fixed to zero whichever of `content`/`summary` the record has, using `""`.
- `dry_run_deletion`'s cascade summary always said "...will also:" followed by zero bullets when
  no cascade stores were wired (the only way the live route calls it today) — reads as "checked,
  found nothing" when the truth is "not checked". Fixed to say so.

Larger, real feature work (not fixed inline):
- **SC-1 (encryption-at-rest) is entirely undeployed.** The stdlib-honest PBKDF2/HKDF/HMAC
  construction in `encryption_manager.py` genuinely round-trips and detects tampering in tests,
  but nothing in `api/`/`infra/` ever calls it — Postgres/SQLite data is stored in plaintext at
  the DB layer today. Same for `integrity_verifier.py`'s Merkle-tree tamper detection (superseded
  in practice by the two independent SHA-256 hash chains in `infra/db/audit_trail.py` and
  `infra/db/privacy_audit.py`, both live). Deploying real at-rest encryption is a deployment-infra
  project, not a code-polish fix.
- **Two divergent, non-interoperable sync implementations exist.** `backend/layer12_privacy/
  sync_coordinator.py` (SyncDelta/ConflictResolutionPolicy, spec-accurate) and `infra/db/
  sync_store.py::PostgresSyncStore` (the one `api/routes/sync.py` actually uses — a simpler blind
  relay keyed by monotonic row id, no per-type conflict resolution). They were likely built at
  different times against the same spec. Needs a decision: retire the unused one, or migrate
  `api/routes/sync.py` onto it and add the conflict-resolution logic the current store lacks.
- **SC-3's richer audit/correction views have no UI or route.** `MemoryAuditView` (7 sections),
  `AuditQueryEngine` (5 query intents), and the 6 `MemoryCorrectionType` operations are unused —
  `GET /memory/audit` returns a much flatter episodic/semantic list built ad hoc in
  `api/routes/memory.py`. Worth wiring only if/when a frontend surface needs it.
- **`privacy_agent.py`'s consent management (`ConsentManager`, 6 consent types) is unused** — no
  route captures or checks user consent for any data category.

---

## Layer 13 — Onboarding & Cold Start (audited 2026-08-04)

Zero bugs in the module — every file faithfully implements its spec section, all 66 tests pass.
Fixed two stale "wired by the orchestrator in production" claims inline (module docstring +
architecture doc §12.2) — no behavior change, just correcting what the code/doc say about
themselves. The most unwired layer of the whole 13-layer pass: only the active-elicitation queue
has a production caller (via a lighter reimplementation in `api/elicitation.py`, not the spec'd
`ElicitationSurfacingPolicy`/`ColdStartEngine`). Full detail: `docs/layer-13-architecture.md` §13.

- **Elicitation answers are asked but never captured.** Nova asks "what should I call you?" and
  "are you a student, or working?" (the two active-elicitation questions with real natural
  triggers wired live) but `PostgresOnboardingStore.record_elicitation` only persists that the
  *question* was surfaced, never the user's *answer* — no code path writes `user_handle` or
  `life_phase` anywhere. The question exists purely to have been asked once. Fix: capture the
  next user turn following a surfaced identity/life-context question (or run a small extraction
  pass over it) and persist the answer into onboarding state / Layer 2 semantic memory. This is
  the single highest-value gap found in this layer — small in code, meaningfully broken in
  product experience.
- **`PassiveElicitationEngine` (8 extractors: vocabulary, emotional style, topic approach,
  disclosure comfort, named people, life context, urgency, communication style) never runs in
  production.** All of Layer 13's "infer before asking" design principle — half the point of the
  layer — is inert. Wiring it means running `extract()` per turn and feeding results into
  whatever replaces/extends `PostgresOnboardingStore`'s state.
- **Production graduation criteria are unreachable, not just simplified.** The real
  `GraduationEvaluator` requires `user_handle`, `life_phase`, `communication_style_profile`, and
  `emotional_baseline_calibrated` to be populated — fields only `ColdStartContextBuilder` writes,
  and nothing calls it. `PostgresOnboardingStore` graduates on a bare session counter instead
  (`session_index >= 5`) because it's the only signal actually available. A real fix means either
  building production up to populate `InitialState` for real, or formally retiring
  `GraduationEvaluator`/`ColdStartContextBuilder`/`FeaturePacingController`/`ColdStartEngine` as
  aspirational-but-superseded and updating the architecture doc to match the session-counter
  design that's actually running. Worth a deliberate decision, not a silent default.
- **`ElicitationSurfacingPolicy` vs. `api/elicitation.py`'s ad hoc reimplementation** — behaviorally
  stricter today (not a safety issue) but the two have diverged from a single spec. Reconcile by
  either calling the real policy class from `api/elicitation.py`, or deleting the unused class and
  updating the doc to describe the simpler rate limit that's actually enforced.
- **`FeaturePacingController`/`FEATURE_INTRODUCTION_REGISTRY` is fully unwired** (already flagged
  in the 2026-07-07 "Live integration update" note; confirmed with a fresh grep this pass). No
  feature in Nova is gated or introduced via this mechanism — features are either always-on or
  gated ad hoc elsewhere (e.g. cold-start's own `proactivity_mode="observe_only"`).

---

All 13 layers now audited. This file is the durable record of what each pass found beyond what
was safe to fix inline — see each `## Layer N` section above for the audited-date and the linked
`docs/layer-N-architecture.md` §"Live wiring status" for full detail.
