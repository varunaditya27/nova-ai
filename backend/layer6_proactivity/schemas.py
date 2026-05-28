# Schemas for Layer 6 — Proactive Engagement Engine
#
# Defines proactive trigger types, intrusion scoring, notification policies, and queue management.
#
# Key schemas:
#   - ProactiveItemType: Enum of outreach types (narrative_thread_followup, goal_milestone_reminder,
#     wellbeing_check, relationship_anniversary, pattern_recognition_coaching, event_anticipation, etc.)
#   - ProactiveItem: A candidate outreach (item_id, type, origin_layer, priority, created_at, scheduled_send, user_engaged)
#   - IntrusionScore: 0.0–1.0 representing how intrusive this outreach would be
#     (computed from: time since last message, DND status, user response patterns, message frequency)
#   - CheckInTrigger: Condition that warrants a proactive message
#   - NotificationEvent: A queued or sent proactive message
#   - NotificationPolicy: User preferences (DND windows, max daily messages, preferred channels, etc.)
#
# Design: All proactive items are prioritized by score. Items expire if user circumstances change.
# User response to proactive messages is tracked and fed back into queue management.
