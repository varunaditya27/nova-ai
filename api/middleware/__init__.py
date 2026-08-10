# API Middleware
#
# Request/response interceptors.
#
# Middleware:
#   - logging.py: Structured request logging (method/path/status/duration; no bodies, may hold PII)
#
# CORS is configured directly in api/main.py (_cors_origins), not a separate middleware file.
# Global exception handlers and rate limiting don't exist yet — single-user local dev posture;
# see frontend/DEFERRED_WORK.md #9.
