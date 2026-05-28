# Pipeline — Conversation Wiring
#
# Core principle: Pipeline contains zero business logic. It is pure orchestration.
# It calls layers in sequence and passes data between them. Refactoring a layer
# never changes pipeline code except the import.
#
# Main components:
#   - conversation_orchestrator.py: Entry point for a user turn
#   - system1_pipeline.py: Fast path (classify → prompt_builder → qwen2.5:7b)
#   - system2_pipeline.py: Full path (empathy_hypothesis → 4a → 4b)
#   - proactive_pipeline.py: Background (L6 trigger → generation → L9 delivery)
#   - state_updater.py: Post-turn async (write memory, update goals/relationship/persona)
#
# No business logic. No decision making. Just wiring.
