# Test: Check-In Engine
#
# Tests:
#   - Trigger check-ins on high-salience moments
#   - Respect DND (do not disturb) windows
#   - Enforce minimum frequency (don't spam)
#   - Calculate intrusion cost and compare to threshold
#
# Fixtures: db_session, sample_conversations, notification_policy
