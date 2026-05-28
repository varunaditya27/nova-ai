# Layer 2, Sub-Component: Context Gate
#
# Responsibility: Apply context-dependent suppression or amplification to recalled memories.
#
# The context gate answers: "Given the current conversational context, emotional state, and
# temporal situation, should this memory be suppressed, amplified, or passed through unchanged?"
#
# Gate logic: G(context, memory_type) → suppression_factor ∈ [0, 2]
#   - 0.0 = completely suppress (memory not recalled)
#   - 1.0 = neutral (pass through)
#   - 2.0 = amplify (memory given higher probability)
#
# Suppression rules:
#   - Crisis state: suppress procedural/working memory; keep episodic/identity
#   - High emotional intensity: amplify episodic memories, suppress analytical
#   - Late night: amplify emotional memories, suppress task/goal memories
#   - Tool-use context: amplify procedural, suppress episodic
#
# Main functions:
#   - apply_context_gate(memory, context) -> GateDecision
#   - get_gate_factor(memory_type, context_state) -> float
#
# Integration:
#   - Called after competitive_recall
#   - Final memories passed to Layer 3/4 with gate factor attached
#   - Gate factors read from config/layer2.yaml
