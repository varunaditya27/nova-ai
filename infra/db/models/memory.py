# Memory Models (Layer 2)
#
# ORM models for:
#   - EpisodicRecord: Episodic memories
#   - SemanticRecord: Semantic fact memories
#   - IdentityRecord: Identity/belief memories
#   - ConsolidationRunRecord: Log of forgetting engine runs
#
# Encrypted at rest (Layer 12 encryption_manager handles encryption/decryption).
# Application layer never sees plaintext of sensitive fields.
