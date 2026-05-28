# Test: Confirmation Gate
#
# Tests:
#   - Classify action into tier: AUTO, SOFT, HARD
#   - AUTO: Execute immediately (web search)
#   - SOFT: Ask user but execute if they don't respond quickly
#   - HARD: Wait for explicit confirmation (send email)
#   - Create pending confirmation record
#
# Fixtures: db_session
