# Schemas for Layer 12 — Privacy & Data Infrastructure
#
# Defines all privacy-related data structures.
#
# Key schemas:
#   - DeletionRequest: User request to delete/forget something
#     (request_id, deletion_type, scope, dry_run_mode, confirmation_required)
#   - DeletionType: Enum (forget_person, forget_topic, forget_session, forget_emotion, full_reset)
#   - DeletionCertificate: Proof that deletion was performed
#     (certificate_id, deletion_request_id, affected_records, verification_hash)
#   - MemoryAuditView: What Nova knows about a user (queryable, correctable)
#   - SyncDelta: Encrypted incremental change for sync
#   - KeyHierarchy: Master key → memory key → session key derivation
#   - IntegrityReport: Merkle hash verification of all stores
#   - ConsentRecord: User consent for data usage/sharing
#
# Design: All deletion and privacy operations are auditable and reversible (with caveats).
