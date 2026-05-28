# State Updater
#
# Responsibility: Post-turn async state updates (never blocks user).
#
# Runs after response is sent to user:
#   1. Write new memories to episodic store
#   2. Update personality vector
#   3. Update relationship states and tie strengths
#   4. Process goal progress
#   5. Detect life events and cascade effects
#   6. Update User World Model
#   7. Trigger consolidation if needed (forgetting engine)
#   8. Log all changes to audit trail (Layer 12)
#
# Main functions:
#   - run_state_update(session_id) → None  (async, fire-and-forget)
#
# Integration:
#   - Called by conversation_orchestrator after response is sent
#   - Triggered async (does not block user)
#   - Reads from session buffer (Layer 2 working memory)
#   - Writes to all persistent stores
#   - Updates Layer 10 longitudinal data
#
# Design: All post-turn writes happen here, not during inference.
# This keeps inference fast and memory operations independent.
