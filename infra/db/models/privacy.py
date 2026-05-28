# Privacy Models (Layer 12)
#
# ORM models for:
#   - DeletionCertificate: Proof of deletion
#   - ConsentRecord: User consent logs
#   - IntegrityCheckRecord: Results of integrity verification runs
#   - SyncDeltaRecord: Encrypted sync deltas (for multi-device sync)
#   - KeyRotationRecord: Log of key rotations
#
# Most fields encrypted. Some integrity/audit fields plaintext for audit trail.
