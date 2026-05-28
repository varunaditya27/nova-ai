# Layer 12, Sub-Component: Selective Deletion
#
# Responsibility: Let users make Nova forget things, with full transparency and control.
#
# Deletion types:
#   1. forget_person: Delete all memories related to a specific person
#   2. forget_topic: Delete all memories related to a topic
#   3. forget_session: Delete all data from a specific session
#   4. forget_emotion: Delete memories with specific emotional valence
#   5. full_reset: Delete all memories (nuke and pave)
#
# Workflow:
#   1. User initiates deletion request
#   2. System shows preview (what will be deleted; dry-run mode)
#   3. User confirms
#   4. Deletion executed (logically flagged, then physically purged post-delay)
#   5. Deletion certificate issued
#
# Main functions:
#   - create_deletion_request(deletion_type, scope, user_confirmation) -> DeletionRequest
#   - preview_deletion(request: DeletionRequest) -> DeletionPreview
#   - execute_deletion(request: DeletionRequest) -> DeletionCertificate
#   - handle_cascade_deletion(primary_deletion) -> list[AffectedRecord]
#   - undo_deletion(certificate_id, time_window) -> bool
#
# Integration:
#   - User-facing API via api/routes/memory.py
#   - Logs all deletions to audit trail
#   - Cascades across all stores (SQL, vector, longitudinal)
#
# Design: Users always have control. Deletions are not instant (grace period for undo).
