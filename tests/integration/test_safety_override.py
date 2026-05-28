# Integration Test: Safety Override
#
# Scenario: User says crisis signal → Safety layer activates → Response is safe
#
# Tests:
#   - Safety layer runs FIRST (before other layers)
#   - Crisis detected correctly
#   - Escalation tier assigned
#   - Response is empathetic but not pushy
#   - Micro-interactions disabled
#   - Proactive features disabled
#
# Fixtures: db_session, crisis_user
