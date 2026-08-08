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
feeds it. Full detail: `docs/layer-1-architecture.md` §16 (initial audit), §17 (config + timezone
follow-up, 2026-08-04).

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
  `docs/layer-1-architecture.md` §17. Layers 2–13 remain unread — wire each as its layer is
  revisited, not as one cross-cutting change (original reasoning still holds).
- **Circadian histogram is UTC-based — `[done]` (2026-08-04, follow-up pass).** Fixed by setting
  a real `config['system']['timezone_offset_hours']` (5.5, IST — single-user personal deployment)
  and threading it through both the live circadian band and the historical `typical_bands`
  histogram so they stay consistent. The same fix was needed in four other UTC-timestamp
  derivations found via grep once the pattern was understood — Layer 1's own `make_fuzzy_labeler`
  same-day/yesterday check (the sole path temporal info reaches the LLM), the Digital Desk
  greeting, the calendar heatmap's day bucketing, and Layer 10's day-of-week pattern detector's
  date derivation — all fixed together; see `docs/layer-1-architecture.md` §17 for the full list
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
`docs/layer-2-architecture.md` §20 (initial audit), §21 (STM + episodic extraction), §22
(narrative-chain linking), §23 (User World Model), §24 (Identity Memory).

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
  scoping decision, deferred). See `docs/layer-2-architecture.md` §23 for the full design,
  including why the read side goes through `build_persona`'s own provider rather than
  `MemoryPacket.uwm_context` (nothing forwards the full packet past `recall()`'s
  `list[memory]`-only contract — same finding as §22's narrative-chain read-side gap).
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
  a real one). See `docs/layer-2-architecture.md` §24 for the full design, including why a
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
  to also extract named entities into `entity_refs`. See `docs/layer-2-architecture.md` §22 for
  the full before/after and what's still **not** closed: nothing reads `active_narrative_chains`
  back into generation — `api/assembly.py::recall`'s hook contract only returns
  `recalled_memories`, and there's no prompt-building consumer waiting for chains even if it did.
- **Episodic memory extraction is a stub, not the LLM summarization it's typed as — `[done]`
  (2026-08-05, follow-up pass, together with the STM item below — they're the same fix).**
  `api/state.py::make_state_update_writer` now summarizes promoted turns via the injected `system1`
  LLM (`_summarize_promoted_turn`, with the same best-effort fallback shape as
  `memory_consolidation_job.py`'s `_generalize`) instead of truncating the raw message. See
  `docs/layer-2-architecture.md` §21 for the full design (including the deliberate choice not to
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
  unreachable in favor of the single arrival check. See §21 for the corrected design, including
  the role filter that keeps Nova's own reply text from ever being promoted as if the user said
  it, and the note that accumulating `stm.turns` still has no prompt-side consumer (§3.1's
  in-session coherence purpose remains undelivered).
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
`docs/layer-3-architecture.md` §17 for full detail. This layer had far less "complete but
unwired" scaffolding than Layers 1-2; most of what's left is smaller connection gaps.

- **`alert_fn` (async CrisisAlert push to Layer 11) is never wired.** [investigated 2026-08-07,
  left unwired] Confirmed Layer 11's `evaluate()` (`backend/layer11_safety/crisis_classifier.py`)
  has no push-receiving counterpart at all — building one would be new Layer 11 surface, not a
  wiring fix. Also confirmed redundant with what already runs: the orchestrator already pulls
  `crisis_active` directly off the returned packet, and Layer 11's own SC-2 scan already runs in
  parallel with the whole pipeline independent of any push. Wiring `alert_fn` would add no safety
  value today — leave unwired; revisit only if Layer 11 ever grows an async intake worth feeding.
- **SC-1 and SC-3 each call `llm_fn` separately** — two LLM calls per turn, not the single shared
  small-model call §14.2 describes. Not a correctness bug (both calls work), but a latency/cost
  gap relative to the documented design. Would need `packet_builder.py` restructured so one LLM
  response feeds both classifiers. [2026-08-07: explicitly deferred by the user — real
  engineering work (prompt/parse contracts for both classifiers, partial-failure degradation),
  not a quick wiring fix.]
- **[done, 2026-08-07]** BES (Background Emotional State) inputs — `episodic_memories` and
  `active_stressors` now forwarded live in `api/assembly.py::classify`
  (`memory_store.active_episodic(user_id)` / `uwm.life_context.active_stressors`), now that
  Layer 2's UWM/episodic write path is real. A serious bug was caught and fixed in the same pass:
  the first version crashed on every turn with real episodic data (naive vs. tz-aware datetime
  subtraction inside `compute_background_state`'s `_recent()`), silently swallowed by `_safe()`
  down to `insufficient_data` — see `docs/layer-3-architecture.md` §18. `psychological_model`
  stays unforwarded (`None`) — out of the UWM narrow-slice's scope (Layer 2 §23), not a Layer 3
  gap.
- **`relationship_depth` and `advice_frustration_count` are still never forwarded.** [investigated
  2026-08-07, blocked] `relationship_depth`'s natural source is `RelationshipState.tie_strength`
  — but confirmed that field is never actually updated live: `PostgresRelationshipStore.record_turn`
  (`infra/db/relationship_store.py`) advances message/session counters and stage but never calls
  `relationship_manager.compute_relationship_state`/`update_tie_strength`, so `tie_strength` stays
  pinned at `0.0` forever in production. Forwarding it as-is would just forward a constant zero —
  the same class of bug this pass exists to catch, not fix. The real fix is a Layer 4 gap (wire
  `record_turn` to actually compute tie-strength deltas per session), tracked here for whoever
  picks up Layer 4's remaining backlog. `advice_frustration_count` has no real source anywhere in
  the codebase — inventing one from `unsolicited_advice_tolerance` (a differently-shaped EMA
  preference score, not a count) would be exactly the "reimplement rather than wire to the real
  module" anti-pattern CLAUDE.md warns against; needs a real tracked counter (Layer 4/5 feature
  work) before this can close.
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

- **[done, 2026-08-08]** `refine()` now calls the real `emotion_refiner.refine_emotion` — full
  five-condition skip policy, factual-preservation validation/reinsertion, voice parameters and
  persona packet threaded in. The feared `ctx.refined` contract break didn't materialize: kept
  its existing "the refinement stage ran this turn" meaning (unaffected by the skip policy),
  rather than conflating it with `RefinementOutput.refinement_applied` ("the text was actually
  rewritten") — see `docs/layer-4-architecture.md` §17.4.
- **[done, 2026-08-08]** SC-1 (persona_resolver), SC-3 (tone_calibrator), SC-4 (drift_detector) now
  run live in `build_persona()`/`plan()`, with a caveat: **SC-1's real inputs are, in practice,
  build-time constants.** `persona_resolver.load_core_anchors` accepts `identity_memory_entries`
  but its own body never reads it (declared "forward-compatibility", not a bug introduced here) —
  so `PersonaState` is identical across every user/turn except mode-dependent `humor_allowed` and
  `known_sensitivities` (always `[]`, needs `psychological_model`). Identity Memory still reaches
  the prompt via `_identity_directive` (a separate path, Layer 2 §24), just not through
  `PersonaState`. SC-4's Check 3 (sycophantic capitulation) is permanently inert — no
  cross-turn Nova-stance history is tracked anywhere; Checks 1/2 work fully. Full detail:
  `docs/layer-4-architecture.md` §17.
- **A real gap found while wiring the above:** `infra/db/relationship_store.py::record_turn`
  advanced `RelationshipState`'s counters/stage but never stamped the stage-derived behavioral
  gates (`memory_reference_policy` etc, §4.4) — fixed by having `build_persona` call
  `compute_relationship_state(persisted=rel)` (idempotent over the persisted counters, no
  `communication_model` passed — see the item below).
- **`build_final_response_packet` wiring collides with System 1/2 routing.** The orchestrator's
  `_run_system1`/`_run_system2` hooks decide whether the Emotion Refiner runs at all (System 1
  skips it structurally); `build_final_response_packet` makes that same decision internally via
  the five-condition skip policy. Wiring the real orchestrator wholesale means deciding which of
  the two owns that decision — a design question to resolve before implementing, not a wiring fix.
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

---

## Layer 5 — Social Intelligence & Coaching (audited 2026-08-04)

The cleanest audit so far: `backend/layer5_relationship/` has zero bugs found and all 63 tests
pass. Nothing was fixed inline this phase because there is nothing small to fix — the entire
layer is complete, tested, and has **zero production callers**, with no existing integration
point to hang a small adapter fix on (unlike Layer 4, which at least had a parallel hand-built
path to forward signals into). Full detail: `docs/layer-5-architecture.md` §15. This is one
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
  `docs/layer-5-architecture.md` §16.3.
- **[done, 2026-08-08]** Per-turn entity/event extraction — `api/state.py::make_social_writer`,
  a new post-turn writer. One LLM call surfaces mentions; `resolve_entity`/`create_node`/
  `extract_events` do the real resolution/attribution work. See §16.2 and §16.5 (four bugs caught
  and fixed in review, each with a regression test: a naive/aware datetime crash identical in
  shape to Layer 3's BES bug, silent merging of distinct same-relationship-type people, a
  permanently-inert recency gate, and same-turn double-counting of a repeated mention).
- **[done, 2026-08-08]** Background pattern-detection job — `background/social_pattern_job.py`,
  registered as `social_pattern_detection` (`background/scheduler.py`'s `JOBS`, now 7 entries),
  fixed weekly interval (see below). Re-identifies patterns across runs by `(pattern_type,
  person_ids_involved)` so `has_been_surfaced` history survives and duplicates don't accumulate
  — a bug caught and fixed in review, see §16.5 point 3/§16.4.
- **UWM social-context write-back was resolved differently than originally scoped.**
  `build_social_context_update` (§9's full `SocialContextUpdate`) is still unreachable, but the
  underlying goal — Layer 5 informing the UWM — is now live via a narrower path: Layer 5's
  per-turn extraction directly projects onto `UWM.relationship_graph.people` (see §16.2), and
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
  - Rejecting tentative (0.70-confidence) entity matches to avoid merging distinct people (§16.5
    point 2) means a person referred to by relationship term rather than name across turns ("my
    sister Maya" then later just "my sister") can create a duplicate node instead of resolving to
    the same one. §3.4's tentative-match confirmation mechanism (surfacing an ambiguous match for
    the user to confirm) doesn't exist in this app — would need a UI surface, not just a backend
    change.
  - SC-4's `PATTERN_REFLECTION` coaching type (the most common one, per `_PATTERN_TO_COACHING`)
    always uses `DeliveryMode.AS_QUESTION` — genuinely live and tested end-to-end this pass — but
    the `INLINE`/`STRENGTH_ACKNOWLEDGMENT`/`SUPPORT_NETWORK_NUDGE` coaching types (from
    `build_opportunity_from_conflict`/`build_support_network_nudge`) were not exercised by an
    end-to-end test; they're real, unmodified functions but worth a follow-up test pass if this
    area gets touched again.

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
  - **[done, 2026-08-09]** `on_deferred_coaching` — now wired. Layer 5's follow-up build
    (2026-08-08) made `proactive_coaching_queue` real; `api/state.py::make_proactive_coaching_writer`
    turns a deferred opportunity into a durable `social_pattern_coaching` `ProactiveItem` via the
    real intake contract. See `docs/layer-6-architecture.md` §16.
  - `on_thread_due` and `on_post_distress_gap` remain blocked on Layer 1/2 respectively — no
    change this pass.

**Correction (2026-08-04, from the Layer 7 audit):** the goal→proactive intake described above as
"the one live intake contract" produces **zero real candidates today**. `goal_checkin_item` needs
a milestone or deadline date on the goal; Layer 7's live extraction path never sets either (SC-5
unwired, and the extractor only returns a free-text deadline description, never a parsed date).
The intake wiring itself is correct — it simply has no populated input yet. See the Layer 7 entry
below. **[resolved, 2026-08-09]**: Layer 7's SC-5 is now wired and gives goals real dated
milestones — see `docs/layer-7-architecture.md` §14. `goal_checkin_item` produces real candidates
today for any goal the decomposition LLM assigns a milestone date to.

**Correction (2026-08-04, from the Layer 1 timezone follow-up):** `evaluate_timing_gate`'s daily
cap (`ctx.proactive_messages_sent_today >= 1`) reads a pre-computed field on `UserTimingContext` —
the day-boundary computation lives entirely with whatever caller builds that context, not in
`timing_gate.py` itself. Not fixable here: SC-3 has zero production callers (see above), so there
is no live call site to check yet. Whoever wires SC-3 needs to make sure "today" is computed with
the same `config['system']['timezone_offset_hours']` Layer 1 uses (`docs/layer-1-architecture.md`
§17) — a raw-UTC day boundary would let the cap reset at the wrong local hour.

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
- **[done, 2026-08-09]** SC-5 (Goal Decomposer) wired — `api/state.py::make_goal_writer` calls
  `decompose_goal` for each newly created goal and persists the resulting milestones/habits;
  `engine.py`'s `Goal(...)` construction now also threads `deadline_description`/
  `deadline_is_inferred`/`has_metric`/`metric_description` through from extraction (previously
  silently dropped). `Goal.milestones`/`Goal.habits`' bare-`list` schema annotation (a serde bug
  that silently round-tripped them as dicts, not `Milestone`/`Habit` objects) was caught and fixed
  in the same pass. `Goal.deadline` (a parsed date) still never populates — no NL date parser
  exists — but milestone `target_date` (LLM-returned as ISO, parsed by `decompose_goal`'s existing
  `_parse_date`) closes the practical gap: `goal_checkin_item` can now produce real candidates.
  See `docs/layer-7-architecture.md` §14.

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
