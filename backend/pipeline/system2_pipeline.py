# System 2 Pipeline
#
# Responsibility: Full path for complex/emotional messages (System 2).
# Calls: Layer 1 → Layer 2 → Layer 3 (full reasoning) → Layer 4 → Groq (Agent 4a + 4b) → Layer 9
#
# Speed target: < 30 seconds total (including two LLM calls)
# Quality: Thoughtful, empathetically refined, reasoning-aware.
#
# Main functions:
#   - run_system2(context) -> FinalResponse
#   - stream_system2(context) -> AsyncGenerator[Event]
#
# Integration:
#   - Called by conversation_orchestrator when cognitive_mode = System2
#   - Calls layer3_reasoning.two_stage_pipeline for full reasoning
#   - Calls infra.llm.groq_client for both Agent 4a and 4b
#   - Full output orchestration via Layer 9
#
# Design: Thorough. Uses empathy hypothesis to shape Agent 4b refinement.
# This is where emotional intelligence shines.
