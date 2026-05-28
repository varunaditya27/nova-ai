# Test: Notification Policy
#
# Tests:
#   - Parse user notification preferences
#   - Respect DND windows (no notifications 10 PM - 8 AM)
#   - Enforce frequency limits (e.g., max 1 per hour)
#   - Calculate intrusion cost and decide "should notify?"
#
# Fixtures: db_session, user_preferences
