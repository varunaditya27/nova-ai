# Layer 12 — Privacy & Data Infrastructure
#
# Core premise: Trust is earned through consistent warmth AND through the knowledge that
# what the user shares is safe, they retain sovereignty over their data, and the system
# cannot be used against them.
#
# Layer 12 is NOT a compliance wrapper. It is the engineering that makes the promise
# of a private, personal AI companion credible in practice.
#
# The tension Layer 12 resolves: Better personalization requires richer data retention;
# better privacy requires less of it. NovaAI does not sacrifice one goal for the other.
#
# Key mechanisms:
#   - On-device processing (all data stays local unless explicitly backed up)
#   - Zero-knowledge encryption (user controls the only copy of keys)
#   - User-controlled deletion (users can make Nova forget, completely and auditably)
#   - Memory audit (transparency about what Nova knows)
#   - Cross-platform sync (encrypted delta sync, zero plaintext outside device)
#
# Main components:
#   - privacy_agent.py: Coordination layer for all privacy operations
#   - encryption_manager.py: Key hierarchy—masterKey → memoryKey → sessionKey
#   - selective_deletion.py: All deletion types + cascade + dry-run + certificate
#   - memory_audit.py: What Nova knows, made transparent and correctable
#   - correction_interface.py: Edit/downgrade/expire/anchor memory entries
#   - sync_coordinator.py: E2E encrypted delta sync
#   - integrity_verifier.py: Merkle hash check of all stores
#   - schemas.py: DeletionRequest, MemoryAuditView, SyncDelta, KeyHierarchy
#
# Fundamental rule: Plaintext never leaves device except with explicit user consent and encryption.
