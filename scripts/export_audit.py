# Export Memory Audit
#
# Utility script: python -m scripts.export_audit --user_id <user_id>
#
# Exports full memory audit for a user to JSON.
#
# Includes:
#   - All episodic memories (topic, emotion, timestamp)
#   - All semantic facts
#   - Identity beliefs and personality vector
#   - Relationship graph
#   - Goals and progress
#   - All deletions/corrections (full audit trail)
#
# Output: JSON file (can be compressed, encrypted, shared for debugging)
#
# Usage: python -m scripts.export_audit --user_id user123 --output /tmp/audit.json
