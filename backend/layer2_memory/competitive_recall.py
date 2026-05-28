# Layer 2, Sub-Component: Competitive Recall
#
# Responsibility: Implement softmax-based probabilistic recall with tunable temperature τ.
#
# This component takes a batch of scored memories and applies softmax with temperature
# to produce a probability distribution over candidates. This enables:
#   - Deterministic recall (τ → 0): highest-scoring memory always wins
#   - Stochastic recall (τ → ∞): all candidates equally likely
#   - Balanced recall (0 < τ < 1): top candidates favored but surprises possible
#
# Design principle: No memory is ever permanently blocked from recall. Even low-scoring
# memories have non-zero probability, which creates the experience of "unexpected but apt" recalls.
#
# Main functions:
#   - competitive_recall(scored_memories, temperature=0.8, top_k=20) -> list[RecalledMemory]
#   - apply_softmax(scores, temperature) -> list[float]
#   - sample_memory(probabilities) -> RecalledMemory
#
# Integration:
#   - Called after recall_scorer completes
#   - Feeds results to context_gate for possible suppression/amplification
#   - Temperature τ read from config/layer2.yaml; can be tuned per-session
