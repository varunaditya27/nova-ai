# System 1 Pipeline
#
# Responsibility: Fast path for casual messages (System 1).
# Calls: Layer 1 → Layer 2 → Layer 3 (classifier) → Layer 4 → qwen2.5:7b → Layer 9
#
# Speed target: < 2 seconds total (including LLM call)
# Quality: Good-enough for casual conversation. Not for complex reasoning or crisis.
#
# Main functions:
#   - run_system1(context) -> FinalResponse
#   - stream_system1(context) -> AsyncGenerator[Token]
#
# Integration:
#   - Called by conversation_orchestrator when cognitive_mode = System1
#   - Calls infra.llm.ollama_client for fast model (qwen2.5:7b)
#   - Skips emotion_refiner (Agent 4b)
#   - Full output orchestration via Layer 9
#
# Design: Fast, lightweight, suitable for banter and quick responses.
