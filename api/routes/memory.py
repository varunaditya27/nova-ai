# Memory Routes
#
# Responsibility: User-facing memory audit and correction interface.
#
# Endpoints:
#   - GET /memory/audit: Return MemoryAuditView (what Nova knows)
#   - GET /memory/{id}: Retrieve a specific memory
#   - PATCH /memory/{id}: Correct or downgrade memory
#   - DELETE /memory/{id}: Request deletion (triggers Layer 12 workflow)
#   - POST /memory/deletion/preview: Preview what will be deleted (dry-run)
#
# All operations go through Layer 12 privacy_agent.
