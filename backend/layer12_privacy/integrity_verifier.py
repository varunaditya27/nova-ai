# Layer 12, Sub-Component: Integrity Verifier
#
# Responsibility: Verify that all stored data has not been tampered with.
#
# Mechanism: Merkle hash tree of all stores.
#   - Compute hash of every record in every store
#   - Combine hashes bottom-up to tree root
#   - Store root hash in secure location
#   - Verify on load: recompute tree, check root matches
#
# Main functions:
#   - verify_integrity(user_id) -> IntegrityReport
#   - compute_merkle_root(store_name) -> bytes
#   - detect_tampering(store_name) -> bool
#   - repair_corrupted_records(store_name) -> RepairResult
#
# Integration:
#   - Called on startup and daily by background job
#   - Reads from all storage backends
#   - Reports to user if tampering detected (paranoia feature)
#
# Design: Paranoia is a feature. User can verify their data has not been modified by outsiders.
