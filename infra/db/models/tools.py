# Tools Models (Layer 8)
#
# ORM models for:
#   - ActionRecord: Log of all tool executions
#   - PendingConfirmation: Confirmation requests awaiting user response
#   - IntegrationCredential: Encrypted OAuth tokens (for calendar, email, etc.)
#
# Credentials encrypted at rest. Action logs not sensitive (just metadata).
