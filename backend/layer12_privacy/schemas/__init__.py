"""Schemas for Layer 12 — Privacy & Data Infrastructure (architecture doc §3-§7).

Pure-stdlib dataclasses + str-enums. Layer 12 is the trust architecture: On-Device Memory (SC-1),
Selective Deletion (SC-2), Memory Audit (SC-3), and Cross-Platform Sync (SC-4), coordinated by the
Privacy Agent. The authoritative deletion taxonomy is the six-type model (the scaffold's older
forget_* names are retired). Stores are duck-typed so the layer stays decoupled from concrete DBs.
"""

from __future__ import annotations

from backend.layer12_privacy.schemas.audit import (
    AuditableFact,
    AuditableMemory,
    AuditQueryResult,
    CorrectionResult,
    MemoryAuditView,
    MemoryCorrectionRequest,
    MemoryCorrectionType,
    ProvenanceRecord,
)
from backend.layer12_privacy.schemas.consent import (
    CONSENT_TYPES,
    _NON_REVOCABLE_CONSENTS,
    ConsentRecord,
)
from backend.layer12_privacy.schemas.deletion import (
    DELETION_CONFIRMATION_REQUIREMENTS,
    DELETION_UNDO_WINDOWS,
    CascadeImpactReport,
    DeletionCertificate,
    DeletionRequest,
    DeletionScope,
    DeletionType,
)
from backend.layer12_privacy.schemas.integrity import IntegrityCheckResult
from backend.layer12_privacy.schemas.sync import (
    ResolvedOperation,
    SyncConfiguration,
    SyncDelta,
    SyncOperation,
)

__all__ = [
    # SC-1
    "IntegrityCheckResult",
    # SC-2
    "DeletionType", "DELETION_UNDO_WINDOWS", "DELETION_CONFIRMATION_REQUIREMENTS",
    "DeletionScope", "CascadeImpactReport", "DeletionRequest", "DeletionCertificate",
    # SC-3
    "AuditableMemory", "AuditableFact", "MemoryAuditView", "AuditQueryResult",
    "ProvenanceRecord", "MemoryCorrectionType", "MemoryCorrectionRequest", "CorrectionResult",
    # SC-4
    "SyncOperation", "SyncDelta", "ResolvedOperation", "SyncConfiguration",
    # consent
    "CONSENT_TYPES", "_NON_REVOCABLE_CONSENTS", "ConsentRecord",
]
