# Layer 4, Sub-Component: Drift Controller
#
# Responsibility: Guard against personality over-adaptation (Nova becoming a shapeshifter).
#
# Problem: If personality is too plastic, Nova adapts to every user whim and loses coherence.
# Solution: Centrality-weighted drift gate that requires strong evidence for high-centrality changes.
#
# Mechanism:
#   - High-centrality beliefs (core identity): require evidence_strength > 0.905 to update
#   - Medium-centrality beliefs (communication style): require > 0.75 to update
#   - Low-centrality beliefs (topic preferences): require > 0.5 to update
#
# Main functions:
#   - should_accept_drift(belief_id, centrality, evidence_strength) -> bool
#   - compute_drift_penalty(magnitude_of_change) -> confidence_reduction
#   - log_drift_attempt(belief_id, proposed_change, acceptance) -> None
#
# Integration:
#   - Called by state_updater before updating any personality belief
#   - Prevents Nova from becoming inconsistent or manipulable
#   - All drift attempts logged to Layer 12 audit trail
#
# Design: Acts as a guardian of identity coherence, not a suppressant of growth.
# Legitimate changes (with high evidence) are accepted; fleeting contradictions are rejected.
