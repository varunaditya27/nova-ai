# Layer 12, Sub-Component: Correction Interface
#
# Responsibility: Let users correct Nova's understanding of them.
#
# Corrections users can make:
#   - "That's wrong—I didn't say that"
#   - "That memory is too old; forget it"
#   - "I was wrong about that; this is what I actually think"
#   - "That personality trait isn't accurate anymore"
#   - "This is embarrassing; downgrade its importance"
#
# Main functions:
#   - apply_correction(memory_id, correction_type, new_value) -> CorrectionResult
#   - downgrade_memory(memory_id, new_importance) -> None
#   - set_memory_expiration(memory_id, expiration_date) -> None
#   - anchor_belief(belief_id, confidence_level) -> None  # anchor identity beliefs
#   - request_memory_review(memory_id, rationale) -> ReviewRequest
#
# Integration:
#   - User-facing interface
#   - All corrections logged to audit trail
#   - Cascades to dependent models (personality vector, goals, relationships)
#
# Design: Corrections are taken seriously. They don't trigger debate—Nova just accepts them.
