# Layer 6, Sub-Component: Notification Policy
#
# Responsibility: Multi-condition gate that determines whether to send proactive messages,
# when to defer them, and when to suppress them entirely.
#
# Gates:
#   1. DND (Do Not Disturb) window: User's configured quiet hours
#   2. Message frequency limit: Max X messages per day; don't exceed
#   3. User response learning: If user ignores > 50% of proactive messages, reduce frequency
#   4. Crisis state: Suppress proactive messages during high-distress periods
#   5. Recency gate: Don't send if user just sent a message < 10 min ago
#   6. Batching: Combine multiple low-priority items into one message
#
# Main functions:
#   - should_send_notification(item: ProactiveItem, context: SessionContext) -> bool
#   - decide_delivery_time(item: ProactiveItem) -> datetime | None
#   - batch_notifications(items: list[ProactiveItem]) -> list[ProactiveItem]
#   - learn_user_preferences_from_response(item_id, user_response) -> None
#
# Integration:
#   - Called after check_in_engine and pattern_detector produce candidates
#   - Reads user preferences from config/layer6.yaml and learned NotificationPolicy
#   - If suppressed, item may be re-queued for later or archived
#   - All delivery decisions logged to audit trail
#
# Design: User always has agency. Notification policy is learned, not forced.
