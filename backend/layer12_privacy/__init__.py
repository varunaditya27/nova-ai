"""Layer 12 — Privacy & Data Infrastructure.

The architecture of trust. Not a compliance wrapper — the engineering that makes the promise of a
private, personal AI companion credible in practice. It resolves the genuine tension (richer
personalization wants more data; privacy wants less) through on-device processing, zero-knowledge
encryption, user-controlled keys, surgical deletion, and full transparency — so the user can give
Nova deep access precisely because they can take it back at any time.

Four sub-components + coordinator:

    SC-1  encryption_manager.py    — key hierarchy + authenticated encryption (+ integrity_verifier.py
                                     Merkle tamper detection)
    SC-2  selective_deletion.py    — execution + certificate (+ deletion_scope.py: request building
                                     /scope resolution; deletion_cascade.py: dry-run cascade/redaction)
    SC-3  memory_audit.py          — transparency view + query intent + provenance
          correction_interface.py  — the six user corrections (edit/downgrade/.../anchor/expire)
    SC-4  sync_coordinator.py      — zero-knowledge encrypted deltas + per-type conflict resolution
    privacy_agent.py               — coordinator: consent, deletion lifecycle, audit, integrity

Design commitments (architecture doc §12):
- The user's data is theirs, not Nova's — unconditional access, correction, export, deletion.
- Privacy is verifiable, not just claimed: Memory Audit, deletion certificates, Merkle integrity,
  and provenance make "Nova only knows what you told it" something you can check.
- Zero-knowledge sync: the server is a dumb relay of opaque ciphertext; it never holds the key.
- Deletion is genuinely surgical — the full cascade (semantic facts, personality, longitudinal
  refs) is surfaced before execution and completed; content is secure-zeroed before removal.

Reconciliation (as-built): the production spec mandates AES-256-GCM / SQLCipher / Argon2id with keys
in the Secure Enclave. The stdlib-only test runtime has no AES, so `encryption_manager` implements a
*real* authenticated-encryption construction from stdlib primitives (PBKDF2-HMAC-SHA256 + HKDF +
SHA-256 CTR keystream + HMAC encrypt-then-MAC) that genuinely round-trips, detects tampering, and
rejects wrong keys; production swaps in AES via the same key hierarchy. The scaffold's older
forget_* deletion names are replaced by the authoritative six-type taxonomy.
"""

from backend.layer12_privacy import (
    correction_interface,
    encryption_manager,
    integrity_verifier,
    memory_audit,
    privacy_agent,
    schemas,
    selective_deletion,
    sync_coordinator,
)
from backend.layer12_privacy.correction_interface import apply_correction
from backend.layer12_privacy.encryption_manager import (
    DecryptionError,
    decrypt,
    derive_master_key,
    derive_session_key,
    encrypt,
    hkdf,
    reencrypt,
)
from backend.layer12_privacy.integrity_verifier import (
    compute_merkle_root,
    detect_tampering,
    run_check,
)
from backend.layer12_privacy.memory_audit import (
    build_provenance,
    classify_query_intent,
    generate_audit_view,
    map_importance_to_label,
    query,
)
from backend.layer12_privacy.privacy_agent import PrivacyAgent
from backend.layer12_privacy.selective_deletion import (
    create_deletion_request,
    dry_run_deletion,
    execute_deletion,
    resolve_scope,
)
from backend.layer12_privacy.sync_coordinator import SyncCoordinator, resolve_conflict
from backend.layer12_privacy.schemas import (
    CONSENT_TYPES,
    DELETION_CONFIRMATION_REQUIREMENTS,
    DELETION_UNDO_WINDOWS,
    AuditableFact,
    AuditableMemory,
    AuditQueryResult,
    CascadeImpactReport,
    ConsentRecord,
    CorrectionResult,
    DeletionCertificate,
    DeletionRequest,
    DeletionScope,
    DeletionType,
    IntegrityCheckResult,
    MemoryAuditView,
    MemoryCorrectionRequest,
    MemoryCorrectionType,
    ProvenanceRecord,
    ResolvedOperation,
    SyncConfiguration,
    SyncDelta,
    SyncOperation,
)

__all__ = [
    # modules
    "correction_interface", "encryption_manager", "integrity_verifier", "memory_audit",
    "privacy_agent", "schemas", "selective_deletion", "sync_coordinator",
    # SC-1
    "DecryptionError", "decrypt", "derive_master_key", "derive_session_key", "encrypt", "hkdf",
    "reencrypt", "compute_merkle_root", "detect_tampering", "run_check",
    # SC-2
    "create_deletion_request", "dry_run_deletion", "execute_deletion", "resolve_scope",
    # SC-3
    "apply_correction", "build_provenance", "classify_query_intent", "generate_audit_view",
    "map_importance_to_label", "query",
    # SC-4
    "SyncCoordinator", "resolve_conflict",
    # coordinator
    "PrivacyAgent",
    # schemas
    "CONSENT_TYPES", "DELETION_CONFIRMATION_REQUIREMENTS", "DELETION_UNDO_WINDOWS",
    "AuditableFact", "AuditableMemory", "AuditQueryResult", "CascadeImpactReport", "ConsentRecord",
    "CorrectionResult", "DeletionCertificate", "DeletionRequest", "DeletionScope", "DeletionType",
    "IntegrityCheckResult", "MemoryAuditView", "MemoryCorrectionRequest", "MemoryCorrectionType",
    "ProvenanceRecord", "ResolvedOperation", "SyncConfiguration", "SyncDelta", "SyncOperation",
]
