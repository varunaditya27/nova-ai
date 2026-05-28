# Logging Middleware
#
# Responsibility: Structured logging of all HTTP requests/responses.
#
# Logs (no PII):
#   - Request method, path, query params (no values)
#   - Request processing time
#   - Response status code
#   - Errors and exceptions (stack traces, no user data)
#
# Zero PII is enforced:
#   - No request body logged
#   - No response body logged
#   - No user IDs in logs (only hashed identifiers if needed)
#   - No credentials, API keys, or tokens logged
