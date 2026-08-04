# Graph Report - backend+docs+api  (2026-07-13)

## Corpus Check
- 203 files · ~208,642 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2268 nodes · 6875 edges · 81 communities detected
- Extraction: 45% EXTRACTED · 55% INFERRED · 0% AMBIGUOUS · INFERRED: 3765 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_API Assembly & Pipeline Wiring|API Assembly & Pipeline Wiring]]
- [[_COMMUNITY_API Dependencies & Memory Arbiter|API Dependencies & Memory Arbiter]]
- [[_COMMUNITY_API Reference & Master Architecture Docs|API Reference & Master Architecture Docs]]
- [[_COMMUNITY_Action Recording & MemoryPrivacy Routes|Action Recording & Memory/Privacy Routes]]
- [[_COMMUNITY_Layer 1 Input Perception Assembler|Layer 1 Input Perception Assembler]]
- [[_COMMUNITY_Admin & Route Registration|Admin & Route Registration]]
- [[_COMMUNITY_Layer 13 Elicitation Queue & Reinforcement|Layer 13 Elicitation Queue & Reinforcement]]
- [[_COMMUNITY_Layer 9 Output Delivery, Voice & Streaming|Layer 9 Output Delivery, Voice & Streaming]]
- [[_COMMUNITY_Layer 6 Proactivity Engine|Layer 6 Proactivity Engine]]
- [[_COMMUNITY_Layer 10 Longitudinal Narrative Engine|Layer 10 Longitudinal Narrative Engine]]
- [[_COMMUNITY_Layer 5 Social Coaching & Relationship|Layer 5 Social Coaching & Relationship]]
- [[_COMMUNITY_Chat Routes & Conversation Orchestrator|Chat Routes & Conversation Orchestrator]]
- [[_COMMUNITY_Layer 12 Privacy Audit & Deletion|Layer 12 Privacy Audit & Deletion]]
- [[_COMMUNITY_Design Specs & Implementation Plans|Design Specs & Implementation Plans]]
- [[_COMMUNITY_Layer 7 Goal Engine & Accountability|Layer 7 Goal Engine & Accountability]]
- [[_COMMUNITY_Layer 11 Safety Agent & Crisis Detection|Layer 11 Safety Agent & Crisis Detection]]
- [[_COMMUNITY_Cold Start & Elicitation Cross-Links|Cold Start & Elicitation Cross-Links]]
- [[_COMMUNITY_Layer 12 Encryption & Sync|Layer 12 Encryption & Sync]]
- [[_COMMUNITY_Persona & Planner Directive Builders|Persona & Planner Directive Builders]]
- [[_COMMUNITY_API App Init & Middleware|API App Init & Middleware]]
- [[_COMMUNITY_Layer 12 Doc Integrity & Key Hierarchy|Layer 12 Doc: Integrity & Key Hierarchy]]
- [[_COMMUNITY_TTS Backend Health Checks|TTS Backend Health Checks]]
- [[_COMMUNITY_Life Calendar Entry Firing|Life Calendar Entry Firing]]
- [[_COMMUNITY_Layer 811 Numbering Reconciliation Note|Layer 8/11 Numbering Reconciliation Note]]
- [[_COMMUNITY_Goal Decomposition Prompt|Goal Decomposition Prompt]]
- [[_COMMUNITY_Goal Status Transitions|Goal Status Transitions]]
- [[_COMMUNITY_Goal-to-Proactive Milestone Handoff|Goal-to-Proactive Milestone Handoff]]
- [[_COMMUNITY_Layer 9 Always-Runs Invariant|Layer 9 Always-Runs Invariant]]
- [[_COMMUNITY_Backend Package Init|Backend Package Init]]
- [[_COMMUNITY_TTS Backends Package Init|TTS Backends Package Init]]
- [[_COMMUNITY_Package Init Marker|Package Init Marker]]
- [[_COMMUNITY_Package Init Marker|Package Init Marker]]
- [[_COMMUNITY_Auth Routes Stub (unimplemented)|Auth Routes Stub (unimplemented)]]
- [[_COMMUNITY_Package Init Marker|Package Init Marker]]
- [[_COMMUNITY_TTS Backend SSML Support|TTS Backend SSML Support]]
- [[_COMMUNITY_TTS Backend Voice Listing|TTS Backend Voice Listing]]
- [[_COMMUNITY_TTS Backend Voice Selection|TTS Backend Voice Selection]]
- [[_COMMUNITY_TTS Backend Auth|TTS Backend Auth]]
- [[_COMMUNITY_Life Calendar Event Registration|Life Calendar Event Registration]]
- [[_COMMUNITY_Recall Scorer Default Weights|Recall Scorer Default Weights]]
- [[_COMMUNITY_Memory Base Importance Constant|Memory Base Importance Constant]]
- [[_COMMUNITY_Memory Type Alias|Memory Type Alias]]
- [[_COMMUNITY_Tool Action Tier Base|Tool Action Tier Base]]
- [[_COMMUNITY_Proactive Context Schema|Proactive Context Schema]]
- [[_COMMUNITY_Proactive Validation Result Schema|Proactive Validation Result Schema]]
- [[_COMMUNITY_Proactive Preferences Schema|Proactive Preferences Schema]]
- [[_COMMUNITY_Voice Request Schema|Voice Request Schema]]
- [[_COMMUNITY_Tool Result Output Schema|Tool Result Output Schema]]
- [[_COMMUNITY_Goal Output Schema|Goal Output Schema]]
- [[_COMMUNITY_Longitudinal Route Registration|Longitudinal Route Registration]]
- [[_COMMUNITY_Relationship Route Registration|Relationship Route Registration]]
- [[_COMMUNITY_Safety Route Registration|Safety Route Registration]]
- [[_COMMUNITY_Tools Route Registration|Tools Route Registration]]
- [[_COMMUNITY_Action Record Serialization Helper|Action Record Serialization Helper]]
- [[_COMMUNITY_API Routes Package Marker|API Routes Package Marker]]
- [[_COMMUNITY_Voice Route Registration|Voice Route Registration]]
- [[_COMMUNITY_Chat Route Registration|Chat Route Registration]]
- [[_COMMUNITY_Onboarding Route Registration|Onboarding Route Registration]]
- [[_COMMUNITY_Goals Route Registration|Goals Route Registration]]
- [[_COMMUNITY_Goal Serialization Helper|Goal Serialization Helper]]
- [[_COMMUNITY_Health Route Registration|Health Route Registration]]
- [[_COMMUNITY_Admin Route Registration|Admin Route Registration]]
- [[_COMMUNITY_Continuity Route Registration|Continuity Route Registration]]
- [[_COMMUNITY_Datetime ISO Helper|Datetime ISO Helper]]
- [[_COMMUNITY_Sync Route Registration|Sync Route Registration]]
- [[_COMMUNITY_Messages Route Registration|Messages Route Registration]]
- [[_COMMUNITY_Datetime ISO Helper (dup)|Datetime ISO Helper (dup)]]
- [[_COMMUNITY_Date Parsing Helper|Date Parsing Helper]]
- [[_COMMUNITY_Memory Route Registration|Memory Route Registration]]
- [[_COMMUNITY_Episodic Memory Serialization Helper|Episodic Memory Serialization Helper]]
- [[_COMMUNITY_Semantic Memory Serialization Helper|Semantic Memory Serialization Helper]]
- [[_COMMUNITY_Sessions Route Registration|Sessions Route Registration]]
- [[_COMMUNITY_Proactive Route Registration|Proactive Route Registration]]
- [[_COMMUNITY_Layer 4 — Persona & Two-Stage Generation (doc)|Layer 4 — Persona & Two-Stage Generation (doc)]]
- [[_COMMUNITY_Layer 5 — Relationship Intelligence (doc)|Layer 5 — Relationship Intelligence (doc)]]
- [[_COMMUNITY_Layer 6 — Proactivity (doc)|Layer 6 — Proactivity (doc)]]
- [[_COMMUNITY_Layer 7 — Goals & Accountability (doc)|Layer 7 — Goals & Accountability (doc)]]
- [[_COMMUNITY_Layer 10 — Longitudinal (doc)|Layer 10 — Longitudinal (doc)]]
- [[_COMMUNITY_Layer 12 — Privacy & Data (doc)|Layer 12 — Privacy & Data (doc)]]
- [[_COMMUNITY_Layer 13 — Onboarding  Cold Start (doc)|Layer 13 — Onboarding / Cold Start (doc)]]
- [[_COMMUNITY_Frontend Spine Foundational Decisions (doc)|Frontend Spine Foundational Decisions (doc)]]

## God Nodes (most connected - your core abstractions)
1. `API route modules. Routers are imported directly by `api.main` (health, chat thi` - 252 edges
2. `ConversationMode` - 130 edges
3. `EmotionVector` - 96 edges
4. `BackgroundEmotionalState` - 77 edges
5. `EpisodicMemory` - 65 edges
6. `AdviceGate` - 61 edges
7. `VoiceParameters` - 60 edges
8. `ToolResult` - 57 edges
9. `ScoredMemory` - 56 edges
10. `EmotionIntentPacket` - 56 edges

## Surprising Connections (you probably didn't know these)
- `dry_run_deletion()` --semantically_similar_to--> `Rationale: defensive fields, never crash`  [AMBIGUOUS] [semantically similar]
  backend/layer12_privacy/selective_deletion.py → backend/layer10_longitudinal/engine.py
- `API route modules. Routers are imported directly by `api.main` (health, chat thi` --uses--> `SyncConfiguration`  [INFERRED]
  api/routes/__init__.py → backend/layer12_privacy/schemas.py
- `API route modules. Routers are imported directly by `api.main` (health, chat thi` --uses--> `EmotionalRecord`  [INFERRED]
  api/routes/__init__.py → backend/layer10_longitudinal/schemas.py
- `API route modules. Routers are imported directly by `api.main` (health, chat thi` --uses--> `EpisodicRecord`  [INFERRED]
  api/routes/__init__.py → backend/layer10_longitudinal/schemas.py
- `API route modules. Routers are imported directly by `api.main` (health, chat thi` --uses--> `SessionRecord`  [INFERRED]
  api/routes/__init__.py → backend/layer10_longitudinal/schemas.py

## Hyperedges (group relationships)
- **Layer 5 Coaching Detection to Injection Pipeline** — packet_builder_build_social_intelligence_packet, coaching_detector_detect_coaching_opportunity, coaching_modifier_inject_observation, schemas_coachingopportunity [INFERRED 0.85]
- **Layer 9 SC-4 to SC-2 to SC-1 to SC-3 Delivery Pipeline** — interaction_orchestrator_deliver, format_adapter_compute_format_spec, micro_interaction_engine_plan_micro_interactions, thinking_pause_compute_thinking_pause, voice_synthesizer_synthesize, interaction_orchestrator_orchestrate_output [INFERRED 0.85]
- **SocialGraph as Shared Substrate Across Layer 5 Sub-Components** — schemas_socialgraph, social_graph_resolve_entity, coaching_detector_gate_1_availability, packet_builder_build_social_context_update, pattern_recognizer_detect_patterns [INFERRED 0.75]
- **Grounded LLM synthesis with factual fallback** — life_narrative_engine_synthesize_chapter, retrospective_generate_retrospective, weekly_summary_generate_weekly_summary [INFERRED 0.85]
- **Never-block, log-and-continue orchestration resilience** — conversation_orchestrator_conversationorchestrator, proactive_pipeline_run_proactive_check, state_updater_run_state_update [INFERRED 0.80]
- **Create -> dry-run -> confirm -> execute deletion lifecycle** — privacy_agent_privacyagent, selective_deletion_create_deletion_request, selective_deletion_dry_run_deletion, selective_deletion_execute_deletion [EXTRACTED 0.90]
- **Score -> Gate -> Effective Score -> Top-K Recall pipeline** — recall_scorer_score_memory, context_gate_gate_value, competitive_recall_effective_score, competitive_recall_select_recall, arbiter_memory_arbiter [INFERRED 0.85]
- **Memory strength decay/reinforce/deletion lifecycle** — memory_strength_initial_strength, memory_strength_decayed_strength, memory_strength_reinforce, memory_strength_deletion_decision, forgetting_engine_decay_sweep [INFERRED 0.80]
- **Post-turn state update: reinforce, persist, audit** — state_updater_state_updater, audit_trail_audittrail, memory_strength_reinforce, memory_store_inmemorymemorystore [INFERRED 0.80]
- **Layer 8 Tool Confirmation Workflow (intent -> params -> gate -> execute -> record)** — tool_manager_toolmanager, confirmation_gate_compute_confirmation_tier, parameter_resolver_next_clarification, action_recorder_actionrecorder, base_plugin_toolplugin [INFERRED 0.85]
- **Layer 11 Crisis Detection & Veto Pipeline** — crisis_classifier_evaluate, safety_agent_safetyagent, escalation_engine_generate_crisis_response, safe_mode_enforcer_enforce_safe_mode, safety_record_safetyrecord [EXTRACTED 0.90]
- **Swappable ToolPlugin Interface Pattern** — base_plugin_toolplugin, calendar_plugin_calendarplugin, email_plugin_emailplugin, notes_plugin_notesplugin, reminders_plugin_remindersplugin, web_search_plugin_websearchplugin [EXTRACTED 0.90]
- **Layer 1 Input Perception five-sub-component pipeline** — service_processinputevent, temporal_resolver_mapcircadianband, implicit_signals_computeimplicitemotionalintensity, multimodal_normalizer_normalize, prosody_extractor_extractprosody, assembler_assemble [EXTRACTED 0.95]
- **Layer 13 Cold Start Engine coordinator composition** — cold_start_engine_coldstartengine, passive_elicitation_passiveelicitationengine, active_elicitation_queue_elicitationqueue, context_constructor_coldstartcontextbuilder, graduation_evaluator_graduationevaluator, feature_pacing_featurepacingcontroller [EXTRACTED 0.95]
- **Layer 7 per-message goal pipeline orchestration** — engine_rungoalpipeline, goal_store_goalstore, progress_monitor_classifyprogresssignal, accountability_modifier_decidegoalreference, goal_extractor_extractgoal [EXTRACTED 0.95]
- **Layer 3 SC-1..SC-6 pipeline synthesizing the EmotionIntentPacket** — emotion_classifier_classify_emotion, intent_classifier_classify_intent, mismatch_detector_detect_mismatch, background_state_compute_background_state, empathy_hypothesis_generate_empathy_hypothesis, mode_resolver_resolve_conversation_mode, packet_builder_build_emotion_intent_packet [EXTRACTED 0.90]
- **Layer 4 Persona Engine SC-1..SC-4 forming the PersonaPacket** — persona_resolver_resolve_persona_state, relationship_manager_compute_relationship_state, tone_calibrator_calibrate_voice, drift_detector_detect_drift, packet_builder_assemble_persona_packet [EXTRACTED 0.90]
- **Two-stage generation: Semantic Planner (4a) + Emotion Refiner (4b) producing FinalResponsePacket** — semantic_planner_generate_semantic_draft, emotion_refiner_refine_emotion, packet_builder_build_final_response_packet, schemas_finalresponsepacket [EXTRACTED 0.85]
- **Layer 6 background proactive cycle (SC-1 -> SC-2 -> SC-3 -> SC-4)** — engine_run_proactive_cycle, queue_manager_proactivequeuemanager, initiative_classifier_classify_initiative, timing_gate_evaluate_timing_gate, message_generator_generate_proactive_message [EXTRACTED 0.95]
- **Composed post-turn writer chain (api/state.py build_app_state)** — state_make_message_writer, state_make_state_update_writer, state_make_goal_writer, state_make_safety_writer, state_make_onboarding_writer, state_make_relationship_writer, state_make_proactive_writer, state_chain_writers [EXTRACTED 0.95]
- **Layer 6 intake contracts (upstream layers -> ProactiveItem)** — intake_on_thread_due, intake_on_post_distress_gap, intake_on_deferred_coaching, intake_on_goal_milestone_approaching, proactive_gen_goal_checkin_item [EXTRACTED 0.90]
- **Digital Desk: /home aggregates Layer 4/5/6/7/10/13 state into one lens** — continuity_home, longitudinal_store_postgreslongitudinalstore, relationship_store_postgresrelationshipstore, message_store_postgresmessagestore, goal_store_postgresgoalstore, proactive_store_postgresproactivequeue, onboarding_store_postgresonboardingstore [INFERRED 0.85]
- **Layer-8 tool confirmation lifecycle: pending -> confirm/deny -> history** — tools_pending_confirmations, tools_confirm_action, tools_deny_action, tools_action_history, schemas_confirmationrequest, schemas_tooloutcome [INFERRED 0.80]
- **Layer-12 selective deletion: dry-run -> execute -> certificate -> privacy audit chain** — memory_delete_memory, selective_deletion_create_deletion_request, selective_deletion_dry_run_deletion, selective_deletion_execute_deletion, privacy_audit_postgresprivacyaudit, memory__episodicdeletionstore [INFERRED 0.85]
- **Crisis detection and veto flow across Layer 3/9/11** — layer_3_architecture_crisis_flag_handling, layer_11_architecture_crisis_detection_engine, layer_11_architecture_escalation_protocol, layer_9_architecture_crisis_hard_override [EXTRACTED 1.00]
- **Two-stage generation: Layer 3 directives feed Layer 4 Agent 4a/4b split** — layer_3_architecture_emotion_intent_packet, layer_4_architecture_semantic_planner_agent4a, layer_4_architecture_emotion_refiner_agent4b, layer_4_architecture_content_tone_separation_rationale [EXTRACTED 0.90]
- **Cold-start overlay constrains Layers 6/10/13 until graduation** — layer_13_architecture_cold_start_engine, layer_13_architecture_cold_start_handling, layer_6_architecture_proactive_queue_manager, layer_10_architecture_life_calendar [EXTRACTED 0.90]
- **Persistence Completion Increment (#1, #2a, #2b, #4)** — pms_design, layer2_write_path_design, goal_persistence_design, safety_persistence_design, onboarding_persistence_design, alembic_migrations_design [EXTRACTED 0.90]
- **Post-turn writer composition via _chain_writers** — make_state_update_writer, make_goal_writer, make_onboarding_writer, make_safety_writer [EXTRACTED 0.90]
- **Full 13-layer /chat + /chat/stream turn integration** — guardrails_hook_adapter, cold_start_hook_adapter, chat_route_component, chat_stream_route [INFERRED 0.75]

## Communities

### Community 0 - "API Assembly & Pipeline Wiring"
Cohesion: 0.03
Nodes (258): _CrisisAssessment, _EmbedderAdapter, _GuardrailResult, guardrails(), Assembly — build the orchestrator's PipelineSteps from real layers + infra clien, # NOTE: pass the RAW user_id (not a uuid5) so recall matches the write path + re, Adapt an infra LLMClient (embed(list) -> list[list]) to Layer 2's Embedder (embe, Orchestrator-shaped view of an SC-2 CrisisSignal (exposes is_crisis + tier). (+250 more)

### Community 1 - "API Dependencies & Memory Arbiter"
Cohesion: 0.03
Nodes (189): api package overview, _attach_uwm(), build_query_embedding(), _current_strength(), memory_arbiter(), The Memory Arbiter — orchestration logic (architecture doc §11).  The single int, Populate the UWM context snapshot, flagging unavailability per §15., Composite recall query embedding (§8.2): a weighted blend that prevents single-m (+181 more)

### Community 2 - "API Reference & Master Architecture Docs"
Cohesion: 0.01
Nodes (192): POST /admin/jobs/{name}, POST /chat, POST /chat/stream (SSE), Echoes (recalled memories surfaced per turn), Goals endpoints (Layer 7), GET /longitudinal/summaries, /latest, Memory + Privacy endpoints (Layer 2/12), GET /messages, /messages/search, bookmarks/milestones (+184 more)

### Community 3 - "Action Recording & Memory/Privacy Routes"
Cohesion: 0.03
Nodes (96): ActionRecorder, SC: Action Recorder (architecture doc §7).  The auditable log of every tool exec, Append an ActionRecord and return its id (§7)., Build and append an ActionRecord from a plugin ToolResult., Update the lifecycle outcome of an existing record (§7)., Flag a record as undone — recorded, never deleted (§7)., Return matching records, most recent first (§7)., capabilities() (+88 more)

### Community 4 - "Layer 1 Input Perception Assembler"
Cohesion: 0.04
Nodes (129): assemble(), compute_composite_prior(), detect_signal_mismatch(), detect_signal_mismatch, Layer 1 · Sub-Component 5 — Input Perception Assembler (architecture doc §7).  N, Validate and compose every sub-component output into the final packet (§7.3)., Conflict rule 1 (§7.2): high implicit intensity overrides a low-vulnerability ba, Conflict rule 2 (§7.2): prosody signals distress.      Layer 1 cannot judge text (+121 more)

### Community 5 - "Admin & Route Registration"
Cohesion: 0.04
Nodes (106): Admin routes — manually trigger a background job (single-user, no auth).  Lets e, run_job(), BaseModel, Chat endpoints — drive a conversation turn through the orchestrator.  `POST /cha, Stream the turn as Server-Sent Events (meta -> token* -> done).      Sync genera, _greeting (time-of-day greeting), _weather (recency-based weather metaphor), calendar() (+98 more)

### Community 6 - "Layer 13 Elicitation Queue & Reinforcement"
Cohesion: 0.05
Nodes (66): ElicitationQueue, ElicitationSurfacingPolicy, INITIAL_ELICITATION_ITEMS, Layer 13 SC-1 — Active Elicitation Queue + Surfacing Policy (architecture doc §4, Highest-priority waiting item whose trigger fired, prereqs met, register appropr, All three conditions must be true simultaneously for an item to surface (§4.4)., ColdStartEngine, Layer 13 — Cold Start Engine coordinator (architecture doc §7).  Temporary overl (+58 more)

### Community 7 - "Layer 9 Output Delivery, Voice & Streaming"
Cohesion: 0.04
Nodes (93): ABC, Base TTS backend interface (architecture doc §5.7).  Abstract base for all TTS p, Uniform interface the Voice Synthesizer calls every TTS provider through., Render ``ssml_text`` to audio, returning an AudioResult (ok flag + bytes/error)., synthesize(), TTSBackend, OrchestratedOutput, compute_format_spec() (+85 more)

### Community 8 - "Layer 6 Proactivity Engine"
Cohesion: 0.04
Nodes (98): _DISTRESS, _default_context(), Layer 6 orchestrator — the background proactive cycle (architecture doc §8).  Ru, Run one Layer 6 evaluation cycle and return the audit output (architecture doc §, run_proactive_cycle(), classify_initiative(), _DELIVERY_PARAMS, _finalize() (+90 more)

### Community 9 - "Layer 10 Longitudinal Narrative Engine"
Cohesion: 0.05
Nodes (84): Rationale: never surface without grounding, Rationale: synthesis, not logging, assemble_context_packet(), Rationale: defensive fields, never crash, Build the Layer10ContextPacket from synthesized sub-component outputs (doc §8)., _add_years(), LifeCalendar, map_entry_to_retrospective_type() (+76 more)

### Community 10 - "Layer 5 Social Coaching & Relationship"
Cohesion: 0.07
Nodes (91): build_opportunity_from_conflict(), build_opportunity_from_pattern(), build_support_network_nudge(), detect_coaching_opportunity(), gate_1_availability(), gate_2_timing(), gate_3_recency(), SC-4 — Coaching Opportunity Detector (architecture doc §6).  Answers a single qu (+83 more)

### Community 11 - "Chat Routes & Conversation Orchestrator"
Cohesion: 0.04
Nodes (65): auth.py (planned auth routes, unimplemented design stub), chat(), chat_stream(), Rationale: confabulation guard, ConversationOrchestrator, Rationale: crisis veto invariant, _handle_crisis (SC-3 escalation), _handle_tool_use (Layer 8 pre-generation) (+57 more)

### Community 12 - "Layer 12 Privacy Audit & Deletion"
Cohesion: 0.06
Nodes (69): Rationale: architecture of trust, apply_correction(), SC-3 — Memory Correction Interface (architecture doc §5.5).  Lets users correct, Apply a user correction to a memory object (architecture doc §5.5)., compute_merkle_root(), detect_tampering(), _leaf(), SC-1 — Integrity Verifier: Merkle tamper detection (architecture doc §3.4).  Run (+61 more)

### Community 13 - "Design Specs & Implementation Plans"
Cohesion: 0.04
Nodes (73): Alembic Migrations — Design Spec, Alembic Migrations Implementation Plan, Motivation: create_all cannot evolve schema (PR #19/#20 pain), Rationale: keep create_all for offline SQLite tests, API Conversation Endpoint — Design Spec, API Conversation Endpoint Implementation Plan, Motivation: no HTTP surface for the 13-layer pipeline, API Read Surface — Design Spec (+65 more)

### Community 14 - "Layer 7 Goal Engine & Accountability"
Cohesion: 0.08
Nodes (55): decide_goal_reference(), SC-4 — Accountability Response Modifier (architecture doc §6).  The in-conversat, Decide whether/how to reference a goal this turn (architecture doc §6.3)., Run the synchronous Layer 7 path for one message (architecture doc §2, §8)., run_goal_pipeline(), _safe(), build_decomposition_prompt(), check_milestone_completion() (+47 more)

### Community 15 - "Layer 11 Safety Agent & Crisis Detection"
Cohesion: 0.08
Nodes (50): _coerce_semantic(), evaluate(), evaluate_longitudinal_pattern(), _lexical_tier(), SC-2 — Crisis Detection Engine (architecture doc §4).  Runs in parallel with the, Run all three detection layers and fuse them into one CrisisSignal (architecture, Detect escalating distress patterns across sessions (architecture doc §4.3 layer, compute_dependency_score() (+42 more)

### Community 16 - "Cold Start & Elicitation Cross-Links"
Cohesion: 0.05
Nodes (46): decide_goal_reference, ElicitationSurfacingPolicy.can_surface, ElicitationQueue.next_surfaceable_item, compute_composite_prior, ColdStartEngine.deactivate, ColdStartEngine.on_message, ColdStartEngine.on_session_end, ColdStartContextBuilder.process_message (+38 more)

### Community 17 - "Layer 12 Encryption & Sync"
Cohesion: 0.1
Nodes (34): Design commitment: zero-knowledge sync, Rationale: stdlib AEAD stand-in for AES-256-GCM, decrypt(), DecryptionError, derive_master_key(), derive_session_key(), encrypt(), hkdf() (+26 more)

### Community 18 - "Persona & Planner Directive Builders"
Cohesion: 0.12
Nodes (14): build_persona(), build_pipeline_steps(), classify(), _elicitation_directive(), perceive(), plan(), Run an async coroutine to completion from sync code (FastAPI threadpool-safe)., recall() (+6 more)

### Community 19 - "API App Init & Middleware"
Cohesion: 0.16
Nodes (12): BaseHTTPMiddleware, Request logging middleware — records method, path, status, duration (no bodies:, RequestLoggingMiddleware, app, _cors_origins(), create_app(), lifespan(), FastAPI application factory + lifespan (boots the infra substrate once).  `uvico (+4 more)

### Community 20 - "Layer 12 Doc: Integrity & Key Hierarchy"
Cohesion: 0.67
Nodes (3): IntegrityVerifier (Merkle root, daily check), KeyHierarchy (master/memory/vector/session/sync keys), SC-1 On-Device Memory

### Community 21 - "TTS Backend Health Checks"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Life Calendar Entry Firing"
Cohesion: 1.0
Nodes (2): LifeCalendar.check_and_fire_due_entries, LifeCalendar.register_new_user

### Community 23 - "Layer 8/11 Numbering Reconciliation Note"
Cohesion: 1.0
Nodes (2): Layer 11 Package Doc: Layer8/Layer11 Reconciliation Note, Layer 8 Package Doc: Layer8/Layer11 Reconciliation Note

### Community 24 - "Goal Decomposition Prompt"
Cohesion: 1.0
Nodes (2): build_decomposition_prompt, decompose_goal

### Community 25 - "Goal Status Transitions"
Cohesion: 1.0
Nodes (2): apply_transition, GoalStatus

### Community 26 - "Goal-to-Proactive Milestone Handoff"
Cohesion: 1.0
Nodes (2): register_milestones_with_layer6, on_goal_milestone_approaching

### Community 27 - "Layer 9 Always-Runs Invariant"
Cohesion: 1.0
Nodes (2): Layer 9 always runs invariant, Layer 9 — Output Delivery

### Community 28 - "Backend Package Init"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "TTS Backends Package Init"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Package Init Marker"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Package Init Marker"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Auth Routes Stub (unimplemented)"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Package Init Marker"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "TTS Backend SSML Support"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "TTS Backend Voice Listing"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "TTS Backend Voice Selection"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "TTS Backend Auth"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Life Calendar Event Registration"
Cohesion: 1.0
Nodes (1): LifeCalendar.register_life_event

### Community 39 - "Recall Scorer Default Weights"
Cohesion: 1.0
Nodes (1): DEFAULT_WEIGHTS

### Community 40 - "Memory Base Importance Constant"
Cohesion: 1.0
Nodes (1): BASE_IMPORTANCE

### Community 41 - "Memory Type Alias"
Cohesion: 1.0
Nodes (1): Memory (type alias)

### Community 42 - "Tool Action Tier Base"
Cohesion: 1.0
Nodes (1): ACTION_TIER_BASE

### Community 43 - "Proactive Context Schema"
Cohesion: 1.0
Nodes (1): ProactiveContext

### Community 44 - "Proactive Validation Result Schema"
Cohesion: 1.0
Nodes (1): ProactiveValidationResult

### Community 45 - "Proactive Preferences Schema"
Cohesion: 1.0
Nodes (1): ProactivePreferences

### Community 46 - "Voice Request Schema"
Cohesion: 1.0
Nodes (1): VoiceRequest

### Community 47 - "Tool Result Output Schema"
Cohesion: 1.0
Nodes (1): ToolResultOut

### Community 48 - "Goal Output Schema"
Cohesion: 1.0
Nodes (1): GoalOut

### Community 49 - "Longitudinal Route Registration"
Cohesion: 1.0
Nodes (1): longitudinal APIRouter

### Community 50 - "Relationship Route Registration"
Cohesion: 1.0
Nodes (1): relationship APIRouter

### Community 51 - "Safety Route Registration"
Cohesion: 1.0
Nodes (1): safety APIRouter

### Community 52 - "Tools Route Registration"
Cohesion: 1.0
Nodes (1): tools APIRouter

### Community 53 - "Action Record Serialization Helper"
Cohesion: 1.0
Nodes (1): _action_out (ActionRecord -> ToolActionOut)

### Community 54 - "API Routes Package Marker"
Cohesion: 1.0
Nodes (1): api.routes package marker

### Community 55 - "Voice Route Registration"
Cohesion: 1.0
Nodes (1): voice APIRouter

### Community 56 - "Chat Route Registration"
Cohesion: 1.0
Nodes (1): chat APIRouter

### Community 57 - "Onboarding Route Registration"
Cohesion: 1.0
Nodes (1): onboarding APIRouter

### Community 58 - "Goals Route Registration"
Cohesion: 1.0
Nodes (1): goals APIRouter

### Community 59 - "Goal Serialization Helper"
Cohesion: 1.0
Nodes (1): _out (Goal -> GoalOut)

### Community 60 - "Health Route Registration"
Cohesion: 1.0
Nodes (1): health APIRouter

### Community 61 - "Admin Route Registration"
Cohesion: 1.0
Nodes (1): admin APIRouter

### Community 62 - "Continuity Route Registration"
Cohesion: 1.0
Nodes (1): continuity APIRouter

### Community 63 - "Datetime ISO Helper"
Cohesion: 1.0
Nodes (1): _iso (datetime -> isoformat helper)

### Community 64 - "Sync Route Registration"
Cohesion: 1.0
Nodes (1): sync APIRouter

### Community 65 - "Messages Route Registration"
Cohesion: 1.0
Nodes (1): messages APIRouter

### Community 66 - "Datetime ISO Helper (dup)"
Cohesion: 1.0
Nodes (1): _iso (datetime -> isoformat helper)

### Community 67 - "Date Parsing Helper"
Cohesion: 1.0
Nodes (1): _parse_dt (str -> datetime, 422 on bad input)

### Community 68 - "Memory Route Registration"
Cohesion: 1.0
Nodes (1): memory APIRouter

### Community 69 - "Episodic Memory Serialization Helper"
Cohesion: 1.0
Nodes (1): _ep_out (EpisodicMemory -> MemoryOut)

### Community 70 - "Semantic Memory Serialization Helper"
Cohesion: 1.0
Nodes (1): _sem_out (SemanticMemory -> SemanticOut)

### Community 71 - "Sessions Route Registration"
Cohesion: 1.0
Nodes (1): sessions APIRouter

### Community 72 - "Proactive Route Registration"
Cohesion: 1.0
Nodes (1): proactive APIRouter

### Community 73 - "Layer 4 — Persona & Two-Stage Generation (doc)"
Cohesion: 1.0
Nodes (1): Layer 4 — Persona & Two-Stage Generation

### Community 74 - "Layer 5 — Relationship Intelligence (doc)"
Cohesion: 1.0
Nodes (1): Layer 5 — Relationship Intelligence

### Community 75 - "Layer 6 — Proactivity (doc)"
Cohesion: 1.0
Nodes (1): Layer 6 — Proactivity

### Community 76 - "Layer 7 — Goals & Accountability (doc)"
Cohesion: 1.0
Nodes (1): Layer 7 — Goals & Accountability

### Community 77 - "Layer 10 — Longitudinal (doc)"
Cohesion: 1.0
Nodes (1): Layer 10 — Longitudinal

### Community 78 - "Layer 12 — Privacy & Data (doc)"
Cohesion: 1.0
Nodes (1): Layer 12 — Privacy & Data

### Community 79 - "Layer 13 — Onboarding / Cold Start (doc)"
Cohesion: 1.0
Nodes (1): Layer 13 — Onboarding / Cold Start

### Community 80 - "Frontend Spine Foundational Decisions (doc)"
Cohesion: 1.0
Nodes (1): Foundational decisions (Next.js, Ivory+Ink, TanStack Query)

## Ambiguous Edges - Review These
- `dry_run_deletion()` → `Rationale: defensive fields, never crash`  [AMBIGUOUS]
  backend/layer12_privacy/selective_deletion.py · relation: semantically_similar_to
- `build_app_state()` → `stream_turn()`  [AMBIGUOUS]
  api/streaming.py · relation: references
- `chat()` → `auth.py (planned auth routes, unimplemented design stub)`  [AMBIGUOUS]
  api/routes/auth.py · relation: conceptually_related_to
- `Layer 8 Plugin Registry (package doc)` → `SMS Plugin (unimplemented stub)`  [AMBIGUOUS]
  backend/layer8_tools/plugins/__init__.py · relation: references
- `Layer 8 Plugin Registry (package doc)` → `Payments Plugin (unimplemented stub)`  [AMBIGUOUS]
  backend/layer8_tools/plugins/__init__.py · relation: references
- `Layer 8 Plugin Registry (package doc)` → `Habit Tracker Plugin (unimplemented stub)`  [AMBIGUOUS]
  backend/layer8_tools/plugins/__init__.py · relation: references
- `api.middleware package marker (planned middleware inventory)` → `error_handlers.py (planned, not present in repo)`  [AMBIGUOUS]
  api/middleware/__init__.py · relation: references
- `api.middleware package marker (planned middleware inventory)` → `security.py (planned CORS/rate-limit, not present in repo)`  [AMBIGUOUS]
  api/middleware/__init__.py · relation: references

## Knowledge Gaps
- **344 isolated node(s):** `Is there something worth saying? Returns the highest-priority observation (§6.4)`, `SC-1 — Length Calibrator (architecture doc §3.6).  Computes a ``(min_chars, max_`, `Return the (min_chars, max_chars) length target for Layer 4 (architecture doc §3`, `SC-1 — Thinking Pause (architecture doc §3.3, §4.2).  Computes the pause (ms) th`, `Return the pre-response thinking pause in ms (0 = none) (architecture doc §3.3).` (+339 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `TTS Backend Health Checks`** (2 nodes): `TTSBackend.health_check()`, `KokoroBackend.health_check()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Life Calendar Entry Firing`** (2 nodes): `LifeCalendar.check_and_fire_due_entries`, `LifeCalendar.register_new_user`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 8/11 Numbering Reconciliation Note`** (2 nodes): `Layer 11 Package Doc: Layer8/Layer11 Reconciliation Note`, `Layer 8 Package Doc: Layer8/Layer11 Reconciliation Note`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Goal Decomposition Prompt`** (2 nodes): `build_decomposition_prompt`, `decompose_goal`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Goal Status Transitions`** (2 nodes): `apply_transition`, `GoalStatus`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Goal-to-Proactive Milestone Handoff`** (2 nodes): `register_milestones_with_layer6`, `on_goal_milestone_approaching`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 9 Always-Runs Invariant`** (2 nodes): `Layer 9 always runs invariant`, `Layer 9 — Output Delivery`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TTS Backends Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init Marker`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init Marker`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Auth Routes Stub (unimplemented)`** (1 nodes): `auth.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init Marker`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TTS Backend SSML Support`** (1 nodes): `TTSBackend.supports_ssml()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TTS Backend Voice Listing`** (1 nodes): `TTSBackend.get_available_voices()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TTS Backend Voice Selection`** (1 nodes): `TTSBackend.set_voice()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TTS Backend Auth`** (1 nodes): `TTSBackend.authenticate()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Life Calendar Event Registration`** (1 nodes): `LifeCalendar.register_life_event`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Recall Scorer Default Weights`** (1 nodes): `DEFAULT_WEIGHTS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Memory Base Importance Constant`** (1 nodes): `BASE_IMPORTANCE`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Memory Type Alias`** (1 nodes): `Memory (type alias)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tool Action Tier Base`** (1 nodes): `ACTION_TIER_BASE`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Proactive Context Schema`** (1 nodes): `ProactiveContext`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Proactive Validation Result Schema`** (1 nodes): `ProactiveValidationResult`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Proactive Preferences Schema`** (1 nodes): `ProactivePreferences`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Voice Request Schema`** (1 nodes): `VoiceRequest`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tool Result Output Schema`** (1 nodes): `ToolResultOut`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Goal Output Schema`** (1 nodes): `GoalOut`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Longitudinal Route Registration`** (1 nodes): `longitudinal APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Relationship Route Registration`** (1 nodes): `relationship APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Safety Route Registration`** (1 nodes): `safety APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tools Route Registration`** (1 nodes): `tools APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Action Record Serialization Helper`** (1 nodes): `_action_out (ActionRecord -> ToolActionOut)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `API Routes Package Marker`** (1 nodes): `api.routes package marker`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Voice Route Registration`** (1 nodes): `voice APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Chat Route Registration`** (1 nodes): `chat APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Onboarding Route Registration`** (1 nodes): `onboarding APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Goals Route Registration`** (1 nodes): `goals APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Goal Serialization Helper`** (1 nodes): `_out (Goal -> GoalOut)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Health Route Registration`** (1 nodes): `health APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Route Registration`** (1 nodes): `admin APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Continuity Route Registration`** (1 nodes): `continuity APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Datetime ISO Helper`** (1 nodes): `_iso (datetime -> isoformat helper)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Sync Route Registration`** (1 nodes): `sync APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Messages Route Registration`** (1 nodes): `messages APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Datetime ISO Helper (dup)`** (1 nodes): `_iso (datetime -> isoformat helper)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Date Parsing Helper`** (1 nodes): `_parse_dt (str -> datetime, 422 on bad input)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Memory Route Registration`** (1 nodes): `memory APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Episodic Memory Serialization Helper`** (1 nodes): `_ep_out (EpisodicMemory -> MemoryOut)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Semantic Memory Serialization Helper`** (1 nodes): `_sem_out (SemanticMemory -> SemanticOut)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Sessions Route Registration`** (1 nodes): `sessions APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Proactive Route Registration`** (1 nodes): `proactive APIRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 4 — Persona & Two-Stage Generation (doc)`** (1 nodes): `Layer 4 — Persona & Two-Stage Generation`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 5 — Relationship Intelligence (doc)`** (1 nodes): `Layer 5 — Relationship Intelligence`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 6 — Proactivity (doc)`** (1 nodes): `Layer 6 — Proactivity`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 7 — Goals & Accountability (doc)`** (1 nodes): `Layer 7 — Goals & Accountability`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 10 — Longitudinal (doc)`** (1 nodes): `Layer 10 — Longitudinal`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 12 — Privacy & Data (doc)`** (1 nodes): `Layer 12 — Privacy & Data`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layer 13 — Onboarding / Cold Start (doc)`** (1 nodes): `Layer 13 — Onboarding / Cold Start`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Spine Foundational Decisions (doc)`** (1 nodes): `Foundational decisions (Next.js, Ivory+Ink, TanStack Query)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `dry_run_deletion()` and `Rationale: defensive fields, never crash`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **What is the exact relationship between `build_app_state()` and `stream_turn()`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `chat()` and `auth.py (planned auth routes, unimplemented design stub)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Layer 8 Plugin Registry (package doc)` and `SMS Plugin (unimplemented stub)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Layer 8 Plugin Registry (package doc)` and `Payments Plugin (unimplemented stub)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Layer 8 Plugin Registry (package doc)` and `Habit Tracker Plugin (unimplemented stub)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `api.middleware package marker (planned middleware inventory)` and `error_handlers.py (planned, not present in repo)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._