# Polish Backlog

Running log of follow-up work surfaced while auditing each layer, one phase at a time (see
CLAUDE.md's "Polish phases" pointer). Each phase reads its layer's code end-to-end, verifies it
does what its architecture doc says, removes dead/bloated code, fixes what's cheaply fixable, and
logs the rest here instead of fixing it on the spot — scope creep between layers is exactly what
this file exists to prevent.

Entries are grouped by the layer that surfaced them. Mark an entry `[done]` with the commit/PR
that closed it instead of deleting the entry — it's the record of what got skipped and why.

**This file is the source of truth.** `docs/PENDING_WORK.md` is a generated filtered view — only
the entries here still missing `[done]`, regrouped for planning. When you close an item, mark it
`[done, DATE]` here first, then update its corresponding bullet in `PENDING_WORK.md` (or remove it
if nothing about the still-open item remains).

---

## Layer 1 — Input Perception (audited 2026-08-04)

Module (`backend/layer1_input/`) itself had no dead code or bloat — every symbol has a caller.
The findings below are gaps between what the module can do and what the live pipeline actually
feeds it. Full detail: `docs/layer-1-architecture.md`.

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
- **`config/layerN.yaml` files are unread — `[done]` for layer1 (2026-08-04, follow-up pass).**
  `backend/layer1_input/config.py::Layer1Config` now reads every `config['layer1']` key live,
  threaded through all 6 sub-component modules as an optional `cfg` param; see
  `docs/layer-1-architecture.md`. Layers 2–13 remain unread — wire each as its layer is
  revisited, not as one cross-cutting change (original reasoning still holds).
- **Circadian histogram is UTC-based — `[done]` (2026-08-04, follow-up pass).** Fixed by setting
  a real `config['system']['timezone_offset_hours']` (5.5, IST — single-user personal deployment)
  and threading it through both the live circadian band and the historical `typical_bands`
  histogram so they stay consistent. The same fix was needed in four other UTC-timestamp
  derivations found via grep once the pattern was understood — Layer 1's own `make_fuzzy_labeler`
  same-day/yesterday check (the sole path temporal info reaches the LLM), the Digital Desk
  greeting, the calendar heatmap's day bucketing, and Layer 10's day-of-week pattern detector's
  date derivation — all fixed together; see `docs/layer-1-architecture.md` for the full list
  and reasoning.
  `api/streaming.py::_circadian_band` (the `/chat/stream` pacing overlay) was deliberately left
  UTC-only — it's cosmetic pacing feel, not a data-attribution path, and already flagged as a
  duplicate implementation in the Layer 9 entry below.

---

## Layer 2 — Cognition & Memory (audited 2026-08-04)

Same shape as Layer 1: every module has a real caller (production or its own tested public API),
no unreachable code. The initial audit found five of the eight sub-components complete and tested
in isolation with **zero live production callers** — bigger in aggregate than Layer 1's gaps,
because each one needed a new detector, table, or LLM step rather than a small adapter. As of the
2026-08-05 follow-up passes below, all eight have real production callers (some narrowed in
scope — see each bullet's `[done]` note for exactly what's still deferred). Full detail:
`docs/layer-2-architecture.md`.

- **User World Model is never created for any real user — `[done]` (2026-08-05, follow-up pass;
  narrow slice).** New `backend/layer2_memory/uwm_updater.py::merge_uwm_update` (pure merge logic)
  + `state_updater`'s new optional `uwm_updater_fn` injection point (mirrors `extractor_fn`) +
  `api/state.py`'s per-turn LLM extraction closure create and merge real UWM rows for
  `profile`/`relationship_graph`/`life_context`. Read side wired too: `api/assembly.py
  ::build_persona` now folds a plain-language UWM directive into the planner prompt via a new
  `uwm_provider`. **Deliberately excluded: `communication_model`** (`backend/layer4_persona
  /style_learning.py` already owns communication style live — building a second version here
  would be exactly the "divergent reimplementation pair" this file already warns about) and
  **`psychological_model`** (attachment/regulation/trigger inference — higher-stakes, separate
  scoping decision, deferred at the time; **[done, 2026-08-09]** the user was asked explicitly
  and chose to build it). See `docs/layer-2-architecture.md` for the full design,
  including why the read side goes through `build_persona`'s own provider rather than
  `MemoryPacket.uwm_context` (nothing forwards the full packet past `recall()`'s
  `list[memory]`-only contract — same finding as the narrative-chain read-side gap noted in `docs/layer-2-architecture.md`).
- **Identity Memory is never seeded or updated — `[done]` (2026-08-05, follow-up pass).**
  `api/state.py::build_app_state` seeds Nova's self-model idempotently on boot
  (`backend/layer2_memory/identity_seed.py::default_identity_beliefs` — the 5 immutable safety
  policies + a small starting personality); a new `backend/layer2_memory/identity.py
  ::detect_identity_contradictions` (one combined LLM call per turn over all non-immutable
  beliefs) feeds the pre-existing `apply_identity_update` via `make_identity_writer`; and
  `make_identity_provider` + `_identity_directive` surface the top-centrality beliefs into the
  planner prompt via `build_persona`. Along the way, fixed a real doc/schema gap:
  `IdentityMemory.evidence_against` was `list[str]` with nowhere to hold a contradiction's numeric
  strength, so multi-session evidence accumulation (§6.3) was structurally impossible before this
  — promoted to `list[IdentityEvidence]` (structured: summary + strength + session + timestamp).
  Also caught and fixed in review: the first version left `apply_identity_update`'s `generate_fn`
  at its offline placeholder default, which would have persisted `"[revised] <statement>"` as
  Nova's literal belief the first time a threshold was crossed — fixed with a real second LLM
  call (`api/state.py::_revise_belief_statement`) and a defense-in-depth change to
  `apply_identity_update` itself (an unchanged/empty `generate_fn` result is now "no update," not
  a real one). See `docs/layer-2-architecture.md` for the full design, including why a
  combined single-call detector (not per-belief, not embedding-pre-filtered) was chosen for this
  app's small, single-user belief set.
- **Narrative-chain linking (SC-8, distinct from Layer 1's narrative *threads*) is orphaned —
  `[done]` (2026-08-05, follow-up pass; write path only).** New `narrative_chain` table +
  `PostgresMemoryStore.save_narrative_chain`/`active_narrative_chains`; `api/state.py
  ::_link_narrative_chains` calls the existing (already tested) `detect_narrative_links` for every
  newly-promoted episode, from inside `make_state_update_writer`'s `_extractor`. A first pass of
  this fix shipped genuinely inert — the formula `0.6·semantic + 0.4·entity_overlap` against a
  `0.65` threshold can never cross threshold when `entity_overlap` is always `0` (nothing
  populated `EpisodicMemory.entity_refs`), so linking could never actually fire — caught in
  review before commit; fixed by extending the existing per-promoted-turn summarization LLM call
  to also extract named entities into `entity_refs`. See `docs/layer-2-architecture.md` for
  the full before/after and what's still **not** closed: nothing reads `active_narrative_chains`
  back into generation — `api/assembly.py::recall`'s hook contract only returns
  `recalled_memories`, and there's no prompt-building consumer waiting for chains even if it did.
- **Episodic memory extraction is a stub, not the LLM summarization it's typed as — `[done]`
  (2026-08-05, follow-up pass, together with the STM item below — they're the same fix).**
  `api/state.py::make_state_update_writer` now summarizes promoted turns via the injected `system1`
  LLM (`_summarize_promoted_turn`, with the same best-effort fallback shape as
  `memory_consolidation_job.py`'s `_generalize`) instead of truncating the raw message. See
  `docs/layer-2-architecture.md` for the full design (including the deliberate choice not to
  batch multiple promotable turns into one multi-turn-synthesized episode).
- **STM buffer (SC-1) is never actually accumulated — `[done]` (2026-08-05, follow-up pass).**
  New `infra/stm_store.py::InProcessSTMStore` (in-process, per-session, RAM-only, LRU-bounded —
  matches the "ephemeral" spec exactly for this single-process deployment) accumulates real turns
  across requests. `make_state_update_writer` checks `should_promote` **on arrival**, immediately
  for every incoming user turn — an eviction-only first cut was caught in review as producing
  essentially zero episodes in practice, since real sessions never come close to filling a
  100-turn window. A second review pass then caught that an *additional* eviction-time check
  (an earlier version of this fix) was dead code — `should_promote` is pure over a turn's own
  fields, which never mutate, so a turn that failed on arrival can only fail again at eviction;
  the eviction-time check and its `promoted_turn_ids` de-duplication guard were removed as
  unreachable in favor of the single arrival check. See `docs/layer-2-architecture.md`'s Live
  Wiring Status section for the corrected design, including the role filter that keeps Nova's own
  reply text from ever being promoted as if the user said it, and the note that accumulating
  `stm.turns` still has no prompt-side consumer (§3.1's in-session coherence purpose remains
  undelivered).
  `max_turns`/`char_limit` raised from 40/12,000 to 100/30,000 for in-session coherence headroom.
  **Real behavior change, chosen deliberately:** Nova now remembers far less by default (only
  emotionally significant or explicitly-flagged moments become long-term memories) — this is what
  the architecture doc actually specifies, not a regression, but it is a materially different
  product experience from the "remembers every message" stub it replaces.
- **Recall's `conversation_mode` is always `default_mode`, not the real one — by design, not a
  gap.** Recall runs before Layer 3 classification (`docs/NOVA_AI_MASTER_ARCHITECTURE.md` §3 steps
  3 vs 5), so there's no mode signal available yet. Documented in §11.2's as-built note; nothing to
  fix here.

---

## Layer 3 — Emotion, Intent & Reasoning (audited 2026-08-04)

Two critical safety/routing bugs found and **fixed** this phase (attribute-name mismatches
invisible to the test suite because every orchestrator test mocks `classify`) — see
`docs/layer-3-architecture.md` for full detail. This layer had far less "complete but
unwired" scaffolding than Layers 1-2; most of what's left is smaller connection gaps.

- **`alert_fn` (async CrisisAlert push to Layer 11) is never wired.** [investigated 2026-08-07,
  left unwired] Confirmed Layer 11's `evaluate()` (`backend/layer11_safety/crisis_classifier.py`)
  has no push-receiving counterpart at all — building one would be new Layer 11 surface, not a
  wiring fix. Also confirmed redundant with what already runs: the orchestrator already pulls
  `crisis_active` directly off the returned packet, and Layer 11's own SC-2 scan already runs in
  parallel with the whole pipeline independent of any push. Wiring `alert_fn` would add no safety
  value today — leave unwired; revisit only if Layer 11 ever grows an async intake worth feeding.
- **[done, 2026-08-09]** SC-1 and SC-3 now share one LLM call per turn instead of two.
  [2026-08-07: explicitly deferred as real engineering work; re-opened and closed 2026-08-09 once
  the user set a "complete end-to-end" bar.] `classify_emotion`/`classify_intent` gained an
  `llm_output` param so a caller can hand them an already-fetched shared result instead of each
  calling `llm_fn` itself; `build_emotion_intent_packet` now computes each classifier's own
  ambiguity condition upfront and fires at most one shared call. Verified with 7 new tests
  (exact call counts, crisis-from-shared-LLM still reaching the packet, heuristic crisis still
  winning over a calmer shared read) plus a live crisis-message run against the real orchestrator.
  See `docs/layer-3-architecture.md`'s follow-up note.
- **[done, 2026-08-07]** BES (Background Emotional State) inputs — `episodic_memories` and
  `active_stressors` now forwarded live in `api/assembly.py::classify`
  (`memory_store.active_episodic(user_id)` / `uwm.life_context.active_stressors`), now that
  Layer 2's UWM/episodic write path is real. A serious bug was caught and fixed in the same pass:
  the first version crashed on every turn with real episodic data (naive vs. tz-aware datetime
  subtraction inside `compute_background_state`'s `_recent()`), silently swallowed by `_safe()`
  down to `insufficient_data` — see `docs/layer-3-architecture.md`. **[done, 2026-08-09]**
  `psychological_model` is now forwarded too, now that Layer 2's Live Wiring Status section notes real extraction was built for it —
  `classify()` pulls it off the same `uwm_provider(user_id)` call already fetching
  `active_stressors`.
- **[done, 2026-08-09]** `relationship_depth` now forwarded live. Its natural source,
  `RelationshipState.tie_strength`, used to stay pinned at `0.0` forever because
  `PostgresRelationshipStore.record_turn` never called `relationship_manager.compute_session_delta`/
  `update_tie_strength`. Fixed at the root (Layer 4, see below) — `record_turn` now genuinely
  updates `tie_strength`, and `api/assembly.py::classify` reads it via the existing
  `relationship_provider` closure and forwards it into `build_emotion_intent_packet`, reaching
  SC-4 Mismatch and SC-5 Empathy Hypothesis for real. See `docs/layer-4-architecture.md`.
  `advice_frustration_count` still has no real source anywhere in the codebase — inventing one
  from `unsolicited_advice_tolerance` (a differently-shaped EMA preference score, not a count)
  would be exactly the "reimplement rather than wire to the real module" anti-pattern CLAUDE.md
  warns against; needs a real tracked counter (Layer 4/5 feature work) before this can close.
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
`docs/layer-4-architecture.md` for full detail. What's left is real feature work, not wiring:

- **[done, 2026-08-08]** `refine()` now calls the real `emotion_refiner.refine_emotion` — full
  five-condition skip policy, factual-preservation validation/reinsertion, voice parameters and
  persona packet threaded in. The feared `ctx.refined` contract break didn't materialize: kept
  its existing "the refinement stage ran this turn" meaning (unaffected by the skip policy),
  rather than conflating it with `RefinementOutput.refinement_applied` ("the text was actually
  rewritten") — see `docs/layer-4-architecture.md`.
- **[done, 2026-08-08]** SC-1 (persona_resolver), SC-3 (tone_calibrator), SC-4 (drift_detector) now
  run live in `build_persona()`/`plan()`. Full detail: `docs/layer-4-architecture.md`.
- **[done, 2026-08-09]** SC-1's real-inputs caveat closed — `load_core_anchors` now actually reads
  `identity_memory_entries`, overriding an anchor's `value` from a real, topically-matching
  `IdentityMemory` belief (category + keyword-hint match, not a blind "closest in category"
  guess) instead of ignoring the parameter entirely. **[done, 2026-08-09]** `known_sensitivities`
  now genuinely populates too — Layer 2's Live Wiring Status section notes real `psychological_model` extraction was built, and
  `build_persona` now fetches and forwards it into `resolve_persona_state`. See
  `docs/layer-4-architecture.md`.
- **[done, 2026-08-09]** SC-4's Check 3 (sycophantic capitulation) is no longer permanently
  inert — "no cross-turn Nova-stance history is tracked anywhere" turned out to be wrong on
  re-investigation: Nova's replies are already tracked, in the real conversation-message log; the
  check just had no reader wired to it. `PostgresMessageStore.recent_by_role` + a new
  `nova_positions_provider` close that. Checks 1/2 already worked fully. See
  `docs/layer-4-architecture.md`.
- **A real gap found while wiring the above:** `infra/db/relationship_store.py::record_turn`
  advanced `RelationshipState`'s counters/stage but never stamped the stage-derived behavioral
  gates (`memory_reference_policy` etc, §4.4) — fixed by having `build_persona` call
  `compute_relationship_state(persisted=rel)` (idempotent over the persisted counters, no
  `communication_model` passed — see the item below).
- **[done, 2026-08-09]** `build_final_response_packet` wiring collision resolved: decided the
  orchestrator keeps owning System 1/2 routing (System 1 structurally skips the refiner, System 2
  always runs it) — unchanged. Re-investigation found every real sub-component the monolithic
  function calls is already wired individually via `build_persona`/`plan`/`refine`; the only real
  gap was the critical-drift (`REFUSE_GRACEFULLY`) hard override, which `plan()`/`refine()` now
  replicate without needing the wholesale rewrite. See `docs/layer-4-architecture.md`.
- **`RelationshipState.compute_relationship_state`'s style-calibration overwrite is a latent
  trap.** `_apply_style_calibration` unconditionally overwrites the four EMA-learned
  communication-style params (`response_length_preference`, etc.) from a coarse one-shot
  `communication_model` derivation whenever a `communication_model` is passed in. `build_persona`
  now calls `compute_relationship_state` live (2026-08-08, see above) but deliberately passes
  `communication_model=None` to sidestep this trap by construction — `communication_model` is
  always `None` anyway (Layer 2's UWM narrow-slice never extracts one). Whoever eventually wires
  that extraction needs to either drop this overwrite or make it additive first, or it will
  silently discard the learned EMA values from `style_learning.py` every turn the moment
  `communication_model` starts being populated and someone naively threads it through.
- **[done, 2026-08-09]** `RelationshipState.record_turn` never computed real tie-strength — the
  real, tested `compute_session_delta`/`update_tie_strength` functions
  (`backend/layer4_persona/relationship_manager.py`) had zero callers from the live per-turn path.
  Fixed: `infra/db/relationship_store.py::record_turn` now accumulates per-turn signals
  (`emotional_intensity`, `had_vulnerability_moment`) into the payload dict — outside the
  dataclass, same convention as `_counted_session_keys` — and applies the accumulated
  `SessionSummary`'s delta the moment a new `session_key` is observed (there's no explicit
  "session end" event in this continuous-chat system, so the delta lands retroactively for the
  session that just ended). `explicit_trust_signals_count`/`repair_occurred` have no real detector
  anywhere yet and stay at their falsy defaults — honest degradation, not a fabricated signal. This
  directly unblocked Layer 3's `relationship_depth` gap above. See `docs/layer-4-architecture.md`.

---

## Layer 5 — Social Intelligence & Coaching (audited 2026-08-04)

The cleanest audit so far: `backend/layer5_relationship/` has zero bugs found and all 63 tests
pass. Nothing was fixed inline this phase because there is nothing small to fix — the entire
layer is complete, tested, and has **zero production callers**, with no existing integration
point to hang a small adapter fix on (unlike Layer 4, which at least had a parallel hand-built
path to forward signals into). Full detail: `docs/layer-5-architecture.md`. This is one
feature to build, in dependency order:

- **[done, 2026-08-08]** Persistence — `social_graph`/`social_event`/`social_pattern` tables
  (`infra/db/models/social.py`, `infra/db/social_store.py`/`social_serde.py`). No `SocialEdge`
  persistence: no real SC-1 function builds edges yet, so nothing invented one — `SocialGraph.edges`
  stays empty until Layer 5 itself grows a real edge-management function. No Alembic revision —
  same as `NarrativeChain` shipped earlier the same day (baseline migration's `create_all` is the
  only path this project currently exercises).
- **[done, 2026-08-08, corrected 2026-08-09]** Orchestrator hook — a new
  `PipelineSteps.social_coaching(ctx, response)` hook runs post-generation, pre-guardrails, in
  both System 1 and System 2. Originally forwarded real inputs into `detect_coaching_opportunity`/
  `inject_observation` directly; corrected to call the real, unmodified Layer 5 orchestrator
  (`packet_builder.build_social_intelligence_packet`) instead, since that module already existed
  with the LLM observation-regeneration step and the deferred-opportunity queue wired in — see
  `docs/layer-5-architecture.md`.
- **[done, 2026-08-08]** Per-turn entity/event extraction — `api/state.py::make_social_writer`,
  a new post-turn writer. One LLM call surfaces mentions; `resolve_entity`/`create_node`/
  `extract_events` do the real resolution/attribution work. See `docs/layer-5-architecture.md`'s
  Live Wiring Status section (four bugs caught
  and fixed in review, each with a regression test: a naive/aware datetime crash identical in
  shape to Layer 3's BES bug, silent merging of distinct same-relationship-type people, a
  permanently-inert recency gate, and same-turn double-counting of a repeated mention).
- **[done, 2026-08-08]** Background pattern-detection job — `background/social_pattern_job.py`,
  registered as `social_pattern_detection` (`background/scheduler.py`'s `JOBS`, now 7 entries),
  fixed weekly interval (see below). Re-identifies patterns across runs by `(pattern_type,
  person_ids_involved)` so `has_been_surfaced` history survives and duplicates don't accumulate
  — a bug caught and fixed in review, see `docs/layer-5-architecture.md`'s Live Wiring Status section.
- **[done, 2026-08-10]** Read API — `GET /people`/`GET /people/{id}` (`api/routes/people.py`),
  reading directly from `PostgresSocialStore`. First real consumer of the persisted `SocialGraph`
  outside the writer path. See `docs/superpowers/specs/2026-08-10-social-graph-api-design.md`.
- **UWM social-context write-back was resolved differently than originally scoped.**
  `build_social_context_update` (the layer's own §9 `SocialContextUpdate`) is still unreachable, but the
  underlying goal — Layer 5 informing the UWM — is now live via a narrower path: Layer 5's
  per-turn extraction directly projects onto `UWM.relationship_graph.people` (see
  `docs/layer-5-architecture.md`'s Live Wiring Status section), and
  became the *sole* source of that projection, replacing Layer 2's own independent people-LLM-call
  (an explicit product decision to avoid two divergent extraction pipelines both guessing "who did
  the user mention"). The richer `SocialContextUpdate` (active conflicts, support-network health,
  engagement trend) is still not built or wired — real feature work if wanted later.
- **New gaps surfaced by wiring this layer for real** (not present in the original audit, since
  nothing exercised the module's actual behavior against real data before):
  - `event_tracker.extract_events`' rule-based pass stores `summary = " ".join(text.split())[:200]`
    — near-verbatim user message text, not a compressed extracted description. Contradicts the
    module's own §10 Constraint 3 ("neutral summary... never the raw conversation text"). Latent
    while the layer had no caller; now a real on-disk surface via `make_social_writer`. Not fixed
    (would mean rewriting `event_tracker.py`'s summary logic, out of scope for this pass) — needs
    its own task if the raw-text storage is unacceptable for the eventual on-device encryption
    story (Layer 12).
  - Rejecting tentative (0.70-confidence) entity matches to avoid merging distinct people means a person referred to by relationship term rather than name across turns ("my
    sister Maya" then later just "my sister") can create a duplicate node instead of resolving to
    the same one. §3.4's tentative-match confirmation mechanism (surfacing an ambiguous match for
    the user to confirm) doesn't exist in this app — would need a UI surface, not just a backend
    change.
  - **[done, 2026-08-09]** SC-4's `PATTERN_REFLECTION` coaching type always uses `DeliveryMode.
    AS_QUESTION` — tested end-to-end since Phase 5; the `STRENGTH_ACKNOWLEDGMENT`/`SUPPORT_
    NETWORK_NUDGE` coaching types (both `DeliveryMode.INLINE`, canned-template observations) now
    have real end-to-end tests too, seeding an actual persisted `SocialPattern` of each matching
    type through the real orchestrator. No code changes needed — the functions already worked.
    See `docs/layer-5-architecture.md`.

---

## Layer 6 — Proactive Engagement Engine (audited 2026-08-04)

Another clean module audit — `backend/layer6_proactivity/` has zero bugs found, 76/76 tests pass,
and matches its architecture doc precisely. Unlike Layer 5, Layer 6 is *partially* live: SC-1's
scoring/expiry runs every 30 minutes via `background/proactive_check_job.py`, and the Layer 7 →
Layer 6 goal-check-in intake (`api/proactive_gen.py`) creates real candidates each turn. Full
detail: `docs/layer-6-architecture.md`.

- **[done, 2026-08-09]** `GET /proactive` no longer returns ungated `content_basis` — it now runs
  every candidate through the real SC-3 `evaluate_timing_gate` server-side, with a live
  `UserTimingContext` built from the persisted stores (SC-3 had zero production callers before
  this). See `docs/layer-6-architecture.md`.
- **[done, 2026-08-09]** SC-4 (Message Generator) and SC-5 (Response Tracker) are wired — product
  decision split this from the transport question, since neither needed one:
  `api/proactive_delivery.py` generates a real message for each gate-passing item inside
  `background/proactive_check_job.py` (reusing the live orchestrator's `build_persona`, not
  re-deriving persona/voice logic), and `POST /proactive/{id}/delivered` +
  `make_proactive_response_writer` close the response-tracking loop via
  `ChatRequest.is_reply_to_proactive`. A live-only bug was found and fixed in the process:
  `build_persona` reads `ctx.input_packet`/`ctx.emotion_intent` directly (not getattr-safe),
  which a bare `SimpleNamespace` background-job context didn't have — silently caught by
  `build_persona`'s own try/except, degrading `voice_parameters` to defaults rather than
  crashing. No test using a stub `steps` object could have caught this; a new regression test
  runs against the real `build_persona`. See `docs/layer-6-architecture.md`.
- **[done, 2026-08-09]** Push transport (SSE) and the frontend consumer are built too — product
  decision: do it now, not defer to a later frontend phase. `GET /proactive/stream` pushes
  gate-passing, message-generated items; `frontend/app/proactive/page.tsx` was fixed to render
  the real `message` (it previously rendered `content_basis` directly — the exact bug the gating
  work was meant to prevent a future consumer from committing). Verified in a real browser via
  Playwright against seeded Postgres state (the Chrome MCP extension wasn't connected in this
  environment). See `docs/layer-6-architecture.md`.
- **Three of four intake contracts are unwired**, each blocked on a different upstream layer, not
  on Layer 6 itself: `on_thread_due` needs Layer 1's narrative-thread detector (Layer 1's own
  audited gap); `on_post_distress_gap` needs a Layer 2 state-updater hook that doesn't exist yet;
  `on_deferred_coaching` needs Layer 5's `proactive_coaching_queue`, unreachable until Layer 5
  itself gets wired (Phase 5 finding). These close automatically as their source layers do —
  nothing to do in Layer 6 itself.
  - **[done, 2026-08-09]** `on_deferred_coaching` — now wired. Layer 5's follow-up build
    (2026-08-08) made `proactive_coaching_queue` real; `api/state.py::make_proactive_coaching_writer`
    turns a deferred opportunity into a durable `social_pattern_coaching` `ProactiveItem` via the
    real intake contract. See `docs/layer-6-architecture.md`.
  - **[done, 2026-08-09]** `on_thread_due` — Layer 1's narrative-thread detector shipped
    (`docs/layer-1-architecture.md`); `make_thread_proactive_writer` calls it for real.
  - **[done, 2026-08-09]** `on_post_distress_gap` — "needs a Layer 2 state-updater hook that
    doesn't exist yet" turned out to be avoidable; `background/distress_gap_job.py` derives the
    real gap directly from already-persisted episodic `emotion_vector` data, no new hook needed.
    See `docs/layer-6-architecture.md`.

**Correction (2026-08-04, from the Layer 7 audit):** the goal→proactive intake described above as
"the one live intake contract" produces **zero real candidates today**. `goal_checkin_item` needs
a milestone or deadline date on the goal; Layer 7's live extraction path never sets either (SC-5
unwired, and the extractor only returns a free-text deadline description, never a parsed date).
The intake wiring itself is correct — it simply has no populated input yet. See the Layer 7 entry
below. **[resolved, 2026-08-09]**: Layer 7's SC-5 is now wired and gives goals real dated
milestones — see `docs/layer-7-architecture.md`. `goal_checkin_item` produces real candidates
today for any goal the decomposition LLM assigns a milestone date to.

**Correction (2026-08-04, from the Layer 1 timezone follow-up):** `evaluate_timing_gate`'s daily
cap (`ctx.proactive_messages_sent_today >= 1`) reads a pre-computed field on `UserTimingContext` —
the day-boundary computation lives entirely with whatever caller builds that context, not in
`timing_gate.py` itself. Not fixable here: SC-3 has zero production callers (see above), so there
is no live call site to check yet. Whoever wires SC-3 needs to make sure "today" is computed with
the same `config['system']['timezone_offset_hours']` Layer 1 uses (`docs/layer-1-architecture.md`) — a raw-UTC day boundary would let the cap reset at the wrong local hour.

---

## Layer 7 — Goals & Accountability Engine (audited 2026-08-04)

The best-wired layer audited so far: `run_goal_pipeline` (SC-1/2/3/4) runs for real every turn.
Module itself is clean — 58/58 tests, matches spec. One real bug fixed, two structural gaps
logged. Full detail: `docs/layer-7-architecture.md`.

- **Fixed:** `api/assembly.py::_goal_directive` was injecting goal-accountability directives
  regardless of conversation mode or relationship stage, violating §6.3's hard blocks (no goal
  references in crisis/emotional_support/casual modes or brand-new relationships) and §6.4's
  single-goal rule. Added the three blocks + capped to one goal; verified end-to-end. Practical
  effect: goal injection now fires much less often, since `casual` (one of the three blocked
  modes) is the default resolved mode for most short turns — this is correct per spec, but a
  real behavior change from what was previously live.
- **[done, 2026-08-09]** SC-4's real output (`GoalContextPacket`) now reaches Layer 4, same-turn.
  `decide_goal_reference` (+ its read-only inputs `get_relevant_goals`/`classify_progress_signal`)
  is pure — it didn't need to run post-turn at all, it just happened to live inside
  `run_goal_pipeline`. `make_goal_provider` now calls it directly, pre-generation, with this
  turn's live context — avoiding the staleness a persist-and-replay fix would have introduced
  against "goals yield to the present moment." `_goal_directive`'s hand-rolled directive and
  duplicated blocked-mode check are gone; the real, progress-differentiated instruction is used
  instead. See `docs/layer-7-architecture.md`.
- **[done, 2026-08-09]** SC-5 (Goal Decomposer) wired — `api/state.py::make_goal_writer` calls
  `decompose_goal` for each newly created goal and persists the resulting milestones/habits;
  `engine.py`'s `Goal(...)` construction now also threads `deadline_description`/
  `deadline_is_inferred`/`has_metric`/`metric_description` through from extraction (previously
  silently dropped). `Goal.milestones`/`Goal.habits`' bare-`list` schema annotation (a serde bug
  that silently round-tripped them as dicts, not `Milestone`/`Habit` objects) was caught and fixed
  in the same pass. `Goal.deadline` (a parsed date) still never populates — no NL date parser
  exists — but milestone `target_date` (LLM-returned as ISO, parsed by `decompose_goal`'s existing
  `_parse_date`) closes the practical gap: `goal_checkin_item` can now produce real candidates.
  See `docs/layer-7-architecture.md`.
- **[done, 2026-08-09]** Goals never reached a terminal status live. Investigating Layer 10's
  Year-in-Review `"achieved"`-string bug surfaced a deeper one: `update_progress_score` deliberately
  leaves `.status` alone on a completed/abandoned signal ("status handled by the transition
  rules"), but nothing in the live per-turn path (`run_goal_pipeline`) was ever applying that rule
  — a goal stayed `"active"` forever no matter what the user said, and `status_changed_at` didn't
  even exist as a field. Fixed: `Goal.status_changed_at` added; `run_goal_pipeline` now transitions
  status + stamps the timestamp on a completed/abandoned signal. Two new regression tests assert on
  `.status` directly (the old test only checked `progress_score`, which is exactly why this was
  invisible). See `docs/layer-7-architecture.md`.
- **[done, 2026-08-09]** `progress_monitor.run_staleness_scan` (§5.6 — decays a goal's status over
  time when the user simply stops mentioning it) now has a real caller:
  `background/goal_staleness_job.py` (weekly), applying each `GoalStateChange` back through the
  real `PostgresGoalStore`. See `docs/layer-7-architecture.md`.

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
- **[done, 2026-08-10] Product decision: the five plugins stay demo/proof-of-concept.** Revisited
  during end-to-end status review — all five (`calendar_plugin.py`, `email_plugin.py`,
  `web_search_plugin.py`, `notes_plugin.py`, `reminders_plugin.py`) run against bare in-memory
  Python dicts with zero external integration (no SMTP/Gmail, no Calendar API, no real search
  provider) and zero Postgres persistence — state is lost on every restart. This was already true
  and always intentional ("local/offline backends, no third-party creds," `api/state.py`), but the
  README previously read as though these were live integrations. Explicit decision: keep the
  architecture as a proof-of-concept, don't build real backends now; README's Layer 8 section and
  `backend/layer8_tools/plugins/__init__.py` now say so plainly instead of overclaiming. Revisit
  only if/when a real deployment actually needs Nova to touch a real inbox/calendar/the internet.

**Re-confirmed, 2026-08-09**: no code under `backend/layer8_tools/` or `api/routes/tools.py`
changed since the audit (`git log --since=2026-08-04` on those paths is empty), no other layer's
work this pass touched them, and the full suite (including all Layer 8 tests) is still green. No
further action needed.

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
- **[done, 2026-08-09]** `OrchestratedOutput`'s event sequence and `UserFormatProfile` are both
  now wired. `UserFormatProfile` got a new `format_profile` table + writer/provider pair, feeding
  the learned length preference back into `deliver()`'s length target. `/chat/stream` now replays
  `thinking_pause`/`backchannel` events as new, additive SSE frames (existing `meta`/`token`/`done`
  frames unchanged) — confirmed with the user that self-edit visual replay specifically is not a
  real product need and was dropped from scope. See `docs/layer-9-architecture.md`.
- **`turn_type`, `urgency_level`, `complexity_score`, `voice_mode` have no live source at all**,
  independent of the forwarding gap: `turn_type` (question/venting/request_advice/etc.) isn't
  computed anywhere in Layers 3-4 today; `urgency_level` doesn't exist on `EmotionIntentPacket`;
  `complexity_score` is computed by Layer 4's `SemanticDraft` but discarded before reaching `ctx`
  (`plan()` in `api/assembly.py` returns only `draft.text`, not the full draft object — same shape
  as the Layer 7 `Layer7Output`-discarding finding); `voice_mode` has no signal in `ChatRequest`
  (consistent with Layer 1's audited `ChatRequest` schema gap). `circadian_band` is the exception —
  it does have a live source and is now forwarded, see below.
- **[done, 2026-08-09]** `emoji_usage_rate`/`avg_user_message_length`/`uses_slang_themselves` were
  declared on `UserFormatProfile` and genuinely consumed by `format_adapter.py`'s emoji-policy/
  slang decisions, but `update_format_profile` never computed any of them — real EMA-blended
  signals now do, off the user's actual message text. `circadian_band` now reaches `deliver()`
  for real too (was silently always `"afternoon"`), and `format_spec_applied` survives onto
  `ctx`/`OrchestratedOutput` (no client consumer exists yet, so no new API field was added ahead
  of one). See `docs/layer-9-architecture.md`.

---

## Layer 10 — Longitudinal Life Layer (audited 2026-08-04)

Module clean (65 tests). Live wiring is partial: 2 of 5 sub-components run as background jobs
(weekly summary, pattern detection); SC-1/4/5 and the `Layer10ContextPacket` read path are
unwired. Two real bugs fixed this phase — see `docs/layer-10-architecture.md` for detail:
a field-name bug (`content_basis_valence` doesn't exist on `EpisodicMemory`, silently zeroing
every episode's emotional intensity) and a hardcoded-empty-list gap (`emotional_records=[]`
meant weekly summaries never had real emotional texture and the emotional-cycle pattern
detector could never fire) — fixed by adding `background/_adapters.py::emotional_records`,
deriving records from the same per-episode `emotion_vector` data already read elsewhere.

- **[done, 2026-08-09]** Pattern detection results are now persisted (`longitudinal_pattern`
  table, re-identified across runs like Layer 5's social patterns) and handed off to Layer 6 via
  a new `on_behavioral_pattern` intake function.
- **[done, 2026-08-09]** `Layer10ContextPacket` now reaches Layer 4 every turn via
  `api/state.py::make_longitudinal_provider` + `api/assembly.py::_longitudinal_directive`. SC-1
  (chapter synthesis, `background/narrative_arc_job.py`) and SC-5 (Life Calendar,
  `background/life_calendar_job.py`) were both built to make this possible.
- **[done, 2026-08-09]** `LifeEvent` detection built end-to-end — a real LLM-driven extractor
  (`backend/layer10_longitudinal/life_event_extractor.py`), persistence
  (`infra/db/longitudinal_store.py::save_life_event`/`life_events`), and wiring into both
  `narrative_arc_job.py` (chapter-boundary detection can now actually fire) and
  `life_calendar_job.py` (the real, previously-uncalled `LifeCalendar.register_life_event` now
  runs for every persisted event). See `docs/layer-10-architecture.md`.
- **[done, 2026-08-09]** SC-4 (Retrospective Engine) now runs live from `life_calendar_job.py`:
  a fired calendar entry that maps to a retrospective type generates and persists a real
  `RetrospectivePacket` and hands it to Layer 6 via a new `on_retrospective_ready` intake
  function; a fired entry that doesn't map to one (the relationship-day milestones SC-5 registers
  for every user) goes through a third new intake function, `on_calendar_entry_due`, discovered
  necessary mid-build since `_ENTRY_TO_RETRO` never mapped those types. See
  `docs/layer-10-architecture.md` and `docs/layer-6-architecture.md` for the full design.
- **Real bug found and fixed while wiring `compute_progress_snapshot` to real `Goal` objects for
  the first time**: it counted achieved goals by `status == "achieved"`, but Layer 7's real
  terminal `GoalStatus` value is `"completed"` — `goals_achieved_lifetime`/`achievement_rate_
  lifetime` would have silently stayed 0 forever. Fixed in `progress_tracker.py`; the existing
  unit test asserting against the wrong status string was fixed too.
- **[done, 2026-08-09]** Year in Review's data-completeness blocker is fixed — `Goal.status_
  changed_at` now exists and gets stamped (Layer 7 follow-up, `docs/layer-7-architecture.md`).
  **[done, 2026-08-09]** Its annual trigger is decided too — the Nova relationship's own day-365
  milestone firing generates and persists a real `YearInReview`, then re-registers itself for the
  following year. See `docs/layer-10-architecture.md`.
- **[done, 2026-08-09]** `upcoming_goal_deadlines`/`recent_life_event`/`primary_active_goals` on
  the assembled context packet are now populated — `assemble_context_packet` already accepted all
  three as real params; `make_longitudinal_provider` just never sourced them. See
  `docs/layer-10-architecture.md`.
- **[done, 2026-08-09]** Layer 6 SC-3 (Timing & Delivery Gate) is wired now (see
  `docs/layer-6-architecture.md`'s Live Wiring Status section) — `GET /proactive` gates every
  queue item through `evaluate_timing_gate`
  regardless of `item_type`, so pattern/retrospective/milestone/year-in-review items are covered
  by the same fix, not just goal check-ins. What's still missing is a *push* channel (no
  transport exists) — the gate now decides correctly, but delivery is still poll-only.

---

## Layer 11 — Safety & Crisis Architecture (audited 2026-08-04)

The best-built and best-wired layer of the entire audit pass: zero bugs found, and — unlike every
other layer — all four sub-components have real production callers (SC-1 guardrails post-gen on
every response, SC-2 crisis detection on every message, SC-3 escalation on the veto path, SC-4
dependency monitor weekly). Nothing needed fixing. Full detail: `docs/layer-11-architecture.md`.

- **[done, 2026-08-09]** SC-2's longitudinal detection layer is now live —
  `api/assembly.py::safety_scan` forwards `episodic_memories`/`emotional_records` (via Layer 10's
  own `_adapters.py`, reused not reimplemented). The "must run before recall completes" concern
  turned out not to block this: `memory_store.active_episodic` is a raw store read, not the
  recall/scoring pipeline — `classify()` already relied on the same fact for BES. The semantic
  layer remains correctly unwired: no fine-tuned classifier model exists to inject. See
  `docs/layer-11-architecture.md`.
- **[done, 2026-08-09]** `SafetyRecord`'s tamper-evident hash chain (§8) is now wired — a new
  `safety_record_entry` table + `PostgresSafetyRecordStore` wraps the real, already-complete
  `SafetyRecord.append()`/`.verify_chain()` (zero callers before this). `make_safety_writer`
  appends a chained entry for every crisis turn; `GET /memory/integrity` and the `integrity_check`
  job now verify three chains, not two. Only `crisis_signal_detected` entries flow through it —
  §8's other entry types have no live call sites of their own yet. See
  `docs/layer-11-architecture.md`.
- **[done, 2026-08-09]** `region` now reads from the real, already-merged
  `config['layer11']['escalation']['default_region']` instead of `build_pipeline_steps`'s
  hardcoded `"india"` default standing in silently forever. See `docs/layer-11-architecture.md`.

---

## Layer 12 — Privacy & Data Infrastructure (audited 2026-08-04)

Same pattern as Layer 5/6/10: a fully-built, fully-tested (62 unit tests, all passing) module
where only a fraction has a production caller. **Only SC-2 (Selective Deletion) is live** —
`api/routes/memory.py`'s `DELETE /memory/{memory_id}` — verified end-to-end including
unrecallability through the `GET /memory/search` keyword fallback (new test:
`tests/unit/api/test_routes_privacy.py::test_deleted_memory_unrecallable_via_keyword_search`).
SC-1, SC-3, SC-4, and `privacy_agent.py` all have zero callers outside their own tests. Full
detail: `docs/layer-12-architecture.md`.

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

**[corrected, 2026-08-09] Not actually two divergent sync implementations.** The original framing
below was a misdiagnosis, investigated and corrected rather than "reconciled": `SyncCoordinator`
(`backend/layer12_privacy/sync_coordinator.py`) is genuinely client-side code — it needs a
device-held `sync_key` the server must never see, by the zero-knowledge design's own definition —
so it has no server caller *by design*, not by neglect. `PostgresSyncStore` is correctly the only
thing this backend-only repo's server could ever call. No code changed; the docs did. See
`docs/layer-12-architecture.md`.

**[done, 2026-08-09]** `dry_run_deletion`'s cascade checks are now genuinely wired into
`DELETE /memory/{id}` (semantic + longitudinal), surfacing two real field-mismatch bugs that would
have crashed on first real use: the semantic check read fields that don't exist on Layer 2's real
`SemanticMemory` (`derived_from_episodes`/`fact_id`/`fact_text` → `supporting_episode_ids`/
`memory_id`/`statement`), and the longitudinal check read `backing_episode_ids` on `WeeklySummary`
— a field that only exists on the unrelated `RetrospectivePacket`. A `UUID`-vs-`str` type
mismatch in the membership check was also found and fixed. `execute_deletion` itself still only
mutates the primary episodic store; deciding what cascade-store *mutation* should mean is a real
product decision, not made here. Personality-vector cascade stays permanently unreported — no
such store exists anywhere in this codebase. See `docs/layer-12-architecture.md`.

Larger, real feature work (not fixed inline):
- **SC-1 (encryption-at-rest) is entirely undeployed.** The stdlib-honest PBKDF2/HKDF/HMAC
  construction in `encryption_manager.py` genuinely round-trips and detects tampering in tests,
  but nothing in `api/`/`infra/` ever calls it — Postgres/SQLite data is stored in plaintext at
  the DB layer today. Same for `integrity_verifier.py`'s Merkle-tree tamper detection (superseded
  in practice by the three independent SHA-256 hash chains in `infra/db/audit_trail.py`,
  `infra/db/safety_record_store.py`, and `infra/db/privacy_audit.py`, all live). Deploying real
  at-rest encryption is a deployment-infra project, not a code-polish fix.
**Re-verified, 2026-08-09**: encryption-at-rest remains a deployment project, not code to wire —
no seam exists to hang key management off of.

**[done, 2026-08-09]** SC-3's audit/correction views are wired: `GET /memory/audit/full`,
`GET /memory/audit/query`, `POST /memory/{id}/correct`. Wiring them for the first time surfaced
the same class of bug already found in `dry_run_deletion` (see `docs/layer-12-architecture.md`'s
Live Wiring Status section) — `_to_auditable_fact` read
`fact_id`/`fact_text`/`category`/`source_episode_ids`, none of which exist on the real
`SemanticMemory`, and would have raised `AttributeError` on first use; `IdentityMemory` needed its
own converter entirely (different real field shape). `apply_correction`'s six correction types
also targeted mostly-nonexistent `EpisodicMemory` fields (`content`, `is_anchored`,
`is_user_downgraded`, `auto_expiry_date`, `is_user_confirmed`, `last_corrected_at`) — silently
no-op'd by `update_episodic`'s `hasattr` guard, so five of six correction types did nothing against
a real memory. `EpisodicMemory` gained those five fields (additive, safe defaults) and `EDIT` now
writes both `content` and `summary`. See `docs/layer-12-architecture.md`.

**[done, 2026-08-09]** `privacy_agent.py`'s `ConsentManager` — product decision: skip. No real
operation in this single-user local deployment needs consent-gating today.

**[done, 2026-08-09]** Cascade-store *mutation* — product decision: redact in place. New
`selective_deletion.redact_cascade` strips deleted-episode references from affected semantic
facts/weekly summaries, wired into `DELETE /memory/{id}`. See `docs/layer-12-architecture.md`.

---

## Layer 13 — Onboarding & Cold Start (audited 2026-08-04)

Zero bugs in the module — every file faithfully implements its spec section, all 66 tests pass.
Fixed two stale "wired by the orchestrator in production" claims inline (module docstring +
the architecture doc) — no behavior change, just correcting what the code/doc say about
themselves. The most unwired layer of the whole 13-layer pass: only the active-elicitation queue
has a production caller (via a lighter reimplementation in `api/elicitation.py`, not the spec'd
`ElicitationSurfacingPolicy`/`ColdStartEngine`). Full detail: `docs/layer-13-architecture.md`.

- **[done, 2026-08-09]** Elicitation answers are now captured. Nova asks "what should I call
  you?" and "are you a student, or working?" but `PostgresOnboardingStore.record_elicitation` only
  ever persisted that the *question* was surfaced, never the *answer*. `api/state.py::
  make_cold_start_writer` now runs the real `ColdStartContextBuilder.process_message` every turn
  while cold-starting, which regex-matches a stated name into `user_handle` the next time the user
  says it in any message — not narrowly tied to being a direct reply to that one question, but a
  real, general capture path. See `docs/layer-13-architecture.md`.
- **[done, 2026-08-09]** `PassiveElicitationEngine` (all 8 extractors) now runs live every turn via
  `make_cold_start_writer`, feeding a real, persisted `InitialState` (new
  `infra/db/initial_state_store.py`). Caught and fixed a bare-`list` serde bug on
  `InitialState.named_relationships` (same pattern as Layers 7/9/10) before it was ever exercised
  against Postgres for real.
- **[done, 2026-08-09]** Production graduation now uses the real `GraduationEvaluator` against the
  real, populated `InitialState` — deliberately **alongside**, not instead of, the session-counter
  fallback (so a terse user is never permanently stuck). Two of the evaluator's 7 required criteria
  had no extractor anywhere in Layer 13 (`emotional_baseline_calibrated`, `primary_topic_areas`) —
  resolved by deriving both from real signals already computed elsewhere (the passive engine's own
  confidence ramp; Layer 2's real episodic `topic_tags`) rather than inventing new extraction
  logic. `FeaturePacingController`/`ColdStartEngine` itself were not instantiated directly — its
  real logic was wired via its own component modules instead, since `ColdStartEngine` bundles
  session-start/feature-pacing concerns unrelated to what needed fixing. See
  `docs/layer-13-architecture.md`.
- **[done, 2026-08-09]** `ElicitationSurfacingPolicy` vs. `api/elicitation.py`'s reimplementation
  reconciled — `select_elicitation` now runs the real `ElicitationQueue.next_surfaceable_item` +
  `ElicitationSurfacingPolicy.can_surface` in sequence (the same two-step gate
  `ColdStartEngine.on_message` uses), not a single looser inline check. See
  `docs/layer-13-architecture.md`.
- **Still unwired, correctly**: `FeaturePacingController`/`FEATURE_INTRODUCTION_REGISTRY` — no
  feature in Nova is gated or introduced via this mechanism, and none was built this pass just to
  give it a caller. `ColdStartEngine`'s `activate_proactivity_engine`/
  `activate_longitudinal_full_mode`/`trigger_first_chapter_creation` hooks remain logging-only —
  the real activation already happens elsewhere, keyed off the same `cold_start_active` flag.
  **Re-verified, 2026-08-09**: still no real feature needing staged introduction exists anywhere
  in this codebase; no code changed.

---

All 13 layers now audited, and every real, bounded gap found along the way has either been fixed
or explicitly, deliberately left open with a stated reason — see each `## Layer N` section above
for the audited-date and the linked `docs/layer-N-architecture.md` §"Live wiring status" for full
detail.

## Cross-cutting: every `api/routes/*.py` file checked against its layer (2026-08-09)

A full pass over all 19 route files in `api/routes/`, verifying each calls the real layer
entrypoint it claims to and forwards the fields CLAUDE.md documents. `auth.py` was a
never-implemented stub (multi-user auth is explicitly out of scope for this single-user
deployment) that wasn't registered in `api/main.py` — **removed outright, 2026-08-10** (a
comment-only file describing routes that don't exist is dead code, not documentation; multi-user
auth can be added fresh if the product ever needs it). Everything else checked out correctly
wired, with one real bug found and fixed:

- **`GET /home`'s `current_chapter` was faked from the wrong data source.** It read the latest
  *weekly summary*'s `dominant_theme`/`week_narrative` — but Layer 10 SC-1 has a real, purpose-
  built `NarrativeArc.current_chapter` (a `LifeChapter` with its own `title`/`narrative_summary`,
  synthesized weekly by `background/narrative_arc_job.py`, shipped earlier this pass) that the
  route never read. Fixed to load the real narrative arc and use its current chapter's title
  (falling back to its narrative summary). See `tests/unit/api/test_routes_conversation.py::
  test_home_desk_surfaces_the_real_current_chapter`.
