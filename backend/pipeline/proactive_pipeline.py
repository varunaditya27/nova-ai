# Proactive Pipeline
#
# Responsibility: Background execution of proactive outreach (Layer 6).
# Runs independently of user-initiated turns.
#
# Workflow:
#   1. Check-in engine evaluates candidates (~30 min poll)
#   2. Notification policy gates (DND, frequency, etc.)
#   3. Anticipatory assistant generates message
#   4. Layer 9 orchestrates delivery
#   5. Response tracker monitors user engagement
#
# Main functions:
#   - run_proactive_check() -> None  (triggered by scheduler)
#   - generate_and_send_proactive_message(item) -> NotificationEvent
#
# Integration:
#   - Called by background/scheduler.py every 30 min
#   - Runs in its own async loop (does not block main conversation pipeline)
#   - Calls Layer 6 components (check_in_engine, anticipatory_assistant)
#   - Delivers via Layer 9
#
# Design: Fully autonomous. User never knows the orchestration happening behind the scenes.
