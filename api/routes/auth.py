# Auth Routes
#
# Responsibility: User authentication and session management.
#
# Endpoints:
#   - POST /auth/register: Create new user account
#   - POST /auth/login: Authenticate and get bearer token
#   - POST /auth/refresh: Refresh expired token
#   - POST /auth/logout: Revoke token
#
# Implementation:
#   - Passwords hashed with bcrypt
#   - JWTs for session tokens
#   - Token expiration enforced
#   - Refresh token rotation for security
