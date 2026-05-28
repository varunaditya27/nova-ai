# Session Models (Layer 1)
#
# ORM models for:
#   - SessionRecord: One row per user session
#   - MessageRecord: One row per user message
#   - ThreadRecord: One row per pending narrative thread
#
# No PII or sensitive data (PII is in memory stores, encrypted by Layer 12).
# Only structural/relational data.
