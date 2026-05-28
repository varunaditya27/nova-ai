# Integration Test: Full System 1 Pipeline
#
# Scenario: User sends casual message → System 1 → Response generated
#
# Tests:
#   - Entire pipeline completes in < 2 seconds
#   - Response is coherent and contextual
#   - Memories are recorded
#   - Emotion is detected
#   - Output formatting is applied
#
# Fixtures: db_session, cold_start_user
