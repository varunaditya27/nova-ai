# Pending Work

A durable, layer-by-layer snapshot of everything still open after the 13-layer polish pass
(`docs/POLISH_BACKLOG.md`) completed on 2026-08-09. Unlike `POLISH_BACKLOG.md` — which is the
running log of *everything found*, done and not-done, in chronological/discovery order — this
file is a point-in-time filter: **only what's not `[done]`**, grouped for planning the next round
of work. When an item here closes, mark it `[done, DATE]` here too (don't delete — same convention
as `POLISH_BACKLOG.md`) and it'll naturally fall out of future summaries.

Cross-reference: each bullet names the `docs/layer-N-architecture.md` section and/or
`docs/POLISH_BACKLOG.md` entry it was distilled from — go there for full technical detail on how a
gap was found and why it wasn't fixed inline.

---

## Layer 1 — Input Perception

- **[done, 2026-08-09]** Narrative-thread creation — real LLM-based extractor
  (`backend/layer1_input/thread_extractor.py`), persisted `PostgresThreadStore`
  (`infra/db/thread_store.py`), and a real Layer 6 handoff (`make_thread_proactive_writer` calls
  `on_thread_due` for real). See `docs/layer-1-architecture.md`.
- **[done, 2026-08-09]** Implicit signals — `ChatRequest` now carries the real additive fields
  (deletion/burst/draft-length/typing-start), wired through `perceive()` into a real
  `ClientMetadata`. `response_latency_ms` is real server-side (no frontend needed, via
  `Session.last_delivered_at`); the rest await frontend instrumentation
  (`docs/FRONTEND_TODO.md`) — `composite_prior`'s `>0.6` gate specifically needs deletion/burst
  data, not just latency, to close (see Layer 3 below). SC-3/SC-4 (multimodal/voice) stay
  correctly unwired — no image/voice/document backend exists anywhere, a separate infra project.
  See `docs/layer-1-architecture.md`.
- **`config/layerN.yaml` unread for layers 2–13.** Only Layer 1 and (as of 2026-08-09) Layer 11's
  `escalation.default_region` read their own config file live. By design, wired one layer at a
  time as each is revisited — not a batch cross-cutting fix.
- **[done, 2026-08-10]** Two dead `UserTemporalProfile` fields — `longest_historical_gap_days`
  wired to a real producer + consumer, `typical_session_duration_minutes` deleted (no plausible
  consumer). See `docs/POLISH_BACKLOG.md`.

## Layer 2 — Cognition & Memory

- **STM buffer (SC-1) accumulates real turns but has no prompt-side reader** — in-session "what
  did I say 3 messages ago" recall is still not live; `stm.turns` is written every turn and never
  read back into generation. Real, bounded engineering work — no product decision needed.
- **Narrative-chain linking's write path is live (SC-8) but nothing reads `active_narrative_chains`
  back into generation** — `api/assembly.py::recall`'s hook contract only returns
  `recalled_memories`, and there's no prompt-building consumer waiting for chains even if it did.
  Same shape of gap as the STM item above.
- **[done, 2026-08-09]** `psychological_model` extraction is built — folded into the existing
  per-turn UWM LLM extraction call in `api/state.py` (no new LLM round-trip), conservatively
  evidence-gated like every other key in that prompt. Stays on-device only, same as the rest of
  the UWM. See `docs/layer-2-architecture.md`.
- **`LifeSituation`/`Stressor` have a few individually-unset fields** (`estimated_resolution`,
  `related_episode_ids`, `duration_days`, `linked_situation_id`) — the classes themselves are
  genuinely constructed every turn, just missing these specific values. Needs new LLM-extraction
  JSON keys plus call-site plumbing (episode ids into the UWM merge step), bigger than a wiring
  fix. See `docs/POLISH_BACKLOG.md`.
- **[done, 2026-08-10]** File-length cleanup (`schemas.py` → package, `api/routes/memory.py` →
  split by layer ownership) and dead-schema pruning (`RelationshipEdge`/`SentimentPoint`/
  `RecurringTheme` deleted — duplicated Layer 5's `SocialEdge` or had no producer/consumer at
  all). See `docs/POLISH_BACKLOG.md`.

## Layer 3 — Emotion, Intent & Reasoning

- **[done, 2026-08-09]** SC-1/SC-3 now share one LLM call per turn instead of two — re-opened and
  closed after the user set a "complete end-to-end" bar (originally deferred 2026-08-07). See
  `docs/layer-3-architecture.md`'s follow-up note.
- **[done, 2026-08-09]** `relationship_depth` now forwarded live — Layer 4's `record_turn` genuinely
  computes `tie_strength` (see Layer 4 below); `classify()` reads it via `relationship_provider`.
  `advice_frustration_count` still has no real source anywhere — would need a genuinely new
  tracked counter (Layer 4/5), not attempted.
- **`composite_prior`'s prior-adjustment branch is forwarded but still unreachable.** Layer 1's
  `implicit_intensity` is no longer a pinned constant (latency is real, 2026-08-09), but hand-
  computed the formula: latency alone maxes `composite_prior` around ~0.50, still below the `>0.6`
  gate. Needs the deletion/burst client fields specifically (`docs/FRONTEND_TODO.md`), not just
  latency. No Layer 3 code change needed once the frontend half closes.
- *(`alert_fn` was investigated and deliberately left unwired — not a gap, a closed decision.)*

## Layer 4 — Persona, Personality & Response Generation

- **[done, 2026-08-09]** `build_final_response_packet` resolved — the orchestrator keeps owning
  System 1/2 routing; the one real gap (critical-drift `REFUSE_GRACEFULLY` hard override) is now
  replicated in `plan()`/`refine()`. See `docs/layer-4-architecture.md`.
- **[done, 2026-08-09]** SC-1's `PersonaState` is no longer build-time-constant — real,
  topically-matching `IdentityMemory` beliefs now override the corresponding anchor's `value`.
  See `docs/layer-4-architecture.md`.
- **[done, 2026-08-09]** SC-4's Check 3 (capitulation) is no longer inert — Nova's real recent
  replies (already tracked in the message log) now feed it. See `docs/layer-4-architecture.md`.
- **[done, 2026-08-09]** `RelationshipState.record_turn` now computes real tie-strength —
  per-turn signals (`emotional_intensity`, `had_vulnerability_moment`, both derived from Layer 3's
  real `EmotionClassification`) accumulate into the payload and `compute_session_delta`/
  `update_tie_strength` apply on session-boundary detection (by `session_key` change, since this
  continuous-chat product has no explicit "session end" event). Unblocked Layer 3's
  `relationship_depth` gap above. See `docs/layer-4-architecture.md`.
- **`compute_relationship_state`'s style-calibration overwrite is a latent trap.**
  `_apply_style_calibration` unconditionally overwrites the four EMA-learned communication-style
  params whenever a `communication_model` is passed in — currently harmless-by-construction only
  because `build_persona` always passes `communication_model=None` (Layer 2's UWM narrow-slice
  never extracts one). Whoever wires that extraction needs to fix this overwrite first, or it will
  silently discard `style_learning.py`'s learned values.

## Layer 5 — Social Intelligence & Coaching

- No `SocialEdge` persistence — no real SC-1 function builds edges yet. Investigated 2026-08-09:
  `docs/layer-5-architecture.md`'s Live Wiring Status section already calls building this from
  scratch "exactly the reimplement-rather-than-wire-to-the-real-module anti-pattern" — a
  deliberate prior decision, not an oversight, left as-is.
- **[done, 2026-08-09]** `event_tracker.extract_events` no longer stores near-verbatim message
  text as its "summary" — the rule-based pass now uses a neutral per-event-type template. See
  `docs/layer-5-architecture.md`.
- Tentative (0.70-confidence) entity-match rejection can create duplicate person nodes across
  turns — no UI confirmation surface exists to resolve the ambiguity instead.
- **[done, 2026-08-09]** Three coaching delivery types (`INLINE`/`STRENGTH_ACKNOWLEDGMENT`/
  `SUPPORT_NETWORK_NUDGE`) now have real end-to-end tests. No code changes needed. See
  `docs/layer-5-architecture.md`.

## Layer 6 — Proactive Engagement Engine

- **[done, 2026-08-09]** Push transport built: `GET /proactive/stream` (SSE) + a real frontend
  consumer (`frontend/app/proactive/page.tsx`, `lib/hooks/useProactiveStream.ts`). Verified live
  in a real browser (Playwright, since the Chrome MCP extension wasn't connected in this
  environment) against seeded Postgres state. See `docs/layer-6-architecture.md`.
- **[done, 2026-08-09]** `GET /proactive` now gates server-side through the real SC-3 Timing &
  Delivery Gate (`evaluate_timing_gate`) with a live `UserTimingContext` — no longer returns raw
  ungated `content_basis`. See `docs/layer-6-architecture.md`.
- **[done, 2026-08-09]** `on_thread_due` and `on_post_distress_gap` are both wired now — neither
  actually needed the blocker it was recorded against. See `docs/layer-6-architecture.md`.
- **[done, 2026-08-09]** SC-4 (real message generation) and SC-5 (response tracking) are wired —
  `api/proactive_delivery.py`, `background/proactive_check_job.py`, `POST /proactive/{id}/
  delivered`, `make_proactive_response_writer`. A live-only `build_persona` AttributeError was
  found and fixed in the same pass. See `docs/layer-6-architecture.md`.

## Layer 7 — Goals & Accountability Engine

- **[done, 2026-08-09]** SC-4's real `GoalContextPacket` now reaches Layer 4, pre-generation and
  same-turn — `decide_goal_reference` is pure/read-only, so it didn't need to run post-turn at
  all. See `docs/layer-7-architecture.md`.
- **[done, 2026-08-09]** `progress_monitor.run_staleness_scan` now has a real weekly caller,
  `background/goal_staleness_job.py`. See `docs/layer-7-architecture.md`.

## Layer 8 — Tool Use & Actions

Nothing pending. Re-confirmed clean 2026-08-09.

## Layer 9 — Output Delivery & Interaction Orchestration

- **[done, 2026-08-09]** `format_spec_applied` now survives onto `ctx`/`OrchestratedOutput` (no
  `ChatResponse` field added — no real client consumer exists yet to justify one).
- **[done, 2026-08-09]** `emoji_usage_rate`/`avg_user_message_length`/`uses_slang_themselves` are
  now real, EMA-computed signals off the user's actual messages.
- **[done, 2026-08-09]** `circadian_band` now reaches `deliver()` for real (was silently always
  `"afternoon"`). `complexity_score`/`turn_type`/`urgency_level`/`voice_mode` still have no live
  source anywhere upstream (`turn_type`/`urgency_level` don't exist yet in Layers 3-4; `voice_mode`
  needs the Layer 1 multimodal gap, which stays correctly unwired — no backend exists). See
  `docs/layer-9-architecture.md`.

## Layer 10 — Longitudinal Life Layer

- **[done, 2026-08-09]** `LifeEvent` detection built end-to-end (extractor, persistence, wiring
  into narrative_arc_job.py's chapter-boundary detection and life_calendar_job.py's real
  `register_life_event` anniversary registration). See `docs/layer-10-architecture.md`.
- **[done, 2026-08-09]** `generate_year_in_review`'s annual trigger is decided — the Nova
  relationship's own day-365 milestone firing generates and persists a real `YearInReview` and
  re-registers itself for the following year. See `docs/layer-10-architecture.md`.
- **[done, 2026-08-09]** `upcoming_goal_deadlines`/`recent_life_event`/`primary_active_goals` on
  the assembled `Layer10ContextPacket` are now populated. See `docs/layer-10-architecture.md`.
- **[done, 2026-08-09]** Layer 6 SC-3 now gates every proactive queue item generically (not just
  goal check-ins), so pattern/retrospective/milestone/year-in-review items are covered too. Still
  no push channel — delivery is poll-only. See `docs/layer-6-architecture.md`.

## Layer 11 — Safety & Crisis Architecture

Nothing pending. The semantic classifier layer stays correctly unwired — no fine-tuned model
exists anywhere to inject; not a gap to close without a model.

## Layer 12 — Privacy & Data Infrastructure

- **Encryption-at-rest is entirely undeployed** — a genuine deployment-infrastructure project
  (SQLCipher/AES-256-GCM key management, container/deployment changes), not code to wire.
  Postgres/SQLite data is plaintext at rest today. Confirmed out of scope, 2026-08-09.
- **[done, 2026-08-09]** SC-3's audit/correction views are wired: `GET /memory/audit/full`,
  `GET /memory/audit/query`, `POST /memory/{id}/correct`. Surfaced and fixed real field-mismatch
  bugs in both `memory_audit.py` and `correction_interface.py` along the way (matched the same
  never-called-with-a-real-object pattern already found in `dry_run_deletion`). See
  `docs/layer-12-architecture.md`.
- **[done, 2026-08-09]** `privacy_agent.py`'s `ConsentManager` — product decision: skip. No real
  operation in this single-user local deployment needs consent-gating today. Left unwired.
- **[done, 2026-08-09]** Cascade-store *mutation* — product decision: redact in place (strip
  references, keep the row), not hard-delete. `selective_deletion.redact_cascade` wired into
  `DELETE /memory/{id}`. See `docs/layer-12-architecture.md`.
- No "personality vector" store exists anywhere in this codebase — that cascade check stays
  permanently unreported by construction, not a bug to fix.

## Layer 13 — Onboarding & Cold Start

Re-verified 2026-08-09:

- **`FeaturePacingController`/`FEATURE_INTRODUCTION_REGISTRY` stays unwired** — no feature in Nova
  is gated or introduced via this mechanism, and none was built just to give it a caller. Revisit
  only if a real feature needing staged introduction gets built.

---

*Generated 2026-08-09 from `docs/POLISH_BACKLOG.md`. Update alongside it as items close.*
