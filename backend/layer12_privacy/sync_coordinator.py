# Layer 12, Sub-Component: Sync Coordinator
#
# Responsibility: Synchronize data across devices WITHOUT ever sending plaintext.
#
# Sync mechanism:
#   1. Device A has new data, encrypted with memoryKey
#   2. A sends encrypted delta to sync server (no plaintext ever leaves device)
#   3. Sync server stores encrypted delta
#   4. Device B polls, receives encrypted delta, decrypts with memoryKey
#   5. B's local stores updated
#
# Main functions:
#   - compute_sync_delta(last_sync_token) -> list[SyncDelta]
#   - apply_sync_delta(delta: SyncDelta) -> None
#   - resolve_sync_conflict(delta_a, delta_b) -> ResolvedDelta
#   - get_sync_status() -> SyncStatus
#
# Integration:
#   - Called by api/routes/sync.py
#   - All deltas encrypted with memoryKey
#   - Server never sees plaintext
#   - Conflict resolution is per-store-type (last-write-wins for simple stores, merge logic for complex)
#
# Design: Zero-knowledge sync. Server is dumb—just a storage box for encrypted blobs.
