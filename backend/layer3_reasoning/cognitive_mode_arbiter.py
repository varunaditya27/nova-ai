# Layer 3, Sub-Component: Cognitive Mode Arbiter
#
# Responsibility: Route to System 1 (fast, emotional, Ollama qwen) or System 2 (full, slow, Groq).
#
# Routes based on signals:
#   System 1 path: casual/informational messages, quick emotional check-ins
#   System 2 path: high emotional intensity, reasoning-heavy, goal/conflict, crisis signals
#
# Risk override: Low-risk override lets System 2 be bypassed for high-confidence casual messages.
#
# Main functions:
#   - route_cognitive_mode(user_message, context, emotion_vector) -> CognitiveModeDecision
#   - evaluate_system1_confidence(message, emotion, context) -> float
#   - needs_system2_empathy_reasoning(emotion_intensity, topic_type) -> bool
#
# Integration:
#   - Calls infra.llm.ollama_client for classifier (lightweight gemma3:4b)
#   - Output consumed by pipeline/system1_pipeline.py and pipeline/system2_pipeline.py
#   - Timing constraints enforced (System 1 < 200ms, System 2 < 1000ms)
