# Conversation Orchestrator
#
# Responsibility: Entry point for a user turn. Calls layers in sequence.
#
# Workflow:
#   1. Call Layer 11 (safety_agent) — runs in parallel with main pipeline
#   2. Call Layer 1 (temporal_resolver) — gets temporal context
#   3. Call Layer 2 (memory_store) — recalls relevant memories
#   4. Call Layer 13 (cold_start_engine) — applies cold start constraints if needed
#   5. Call Layer 3 (two_stage_pipeline) — routes to System 1/2, generates reasoning
#   6. Call Layer 4 (prompt_builder) — builds system prompt from context
#   7. If Layer 11 detected crisis: route to crisis response
#   8. Else: Call Layer 3 LLM agents (semantic_planner, emotion_refiner)
#   9. Call Layer 9 (interaction_orchestrator) — orchestrates delivery
#   10. Return OrchestratedOutput to user
#   11. Trigger state_updater (post-turn async)
#
# Main functions:
#   - run_conversation_turn(user_id, message_text) -> OrchestratedOutput
#   - stream_conversation_turn(same) -> AsyncGenerator[OutputEvent]
#
# Integration:
#   - Called by api/routes/chat.py
#   - Routes to system1_pipeline or system2_pipeline based on mode_decision
#   - Triggers state_updater post-turn
#
# Design: Pure orchestration. No logic. Just sequencing.
