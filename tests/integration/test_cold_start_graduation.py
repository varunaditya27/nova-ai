# Integration Test: Cold Start Graduation
#
# Scenario: New user starts → Feature pacing applies → Graduation reached
#
# Tests:
#   - Message 1-2: Basic chat only, passive elicitation
#   - Message 3: Relationships feature unlocked
#   - Message 5+: Goals feature unlocked
#   - Day 1-2: Proactivity still locked
#   - Graduation criteria: min messages + min time + context + activity
#   - Post-graduation: All features available
#
# Fixtures: db_session, cold_start_user
