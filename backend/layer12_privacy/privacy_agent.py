"""Privacy Agent — Layer 12 coordinator (architecture doc §7).

The persistent on-device service that coordinates all four sub-components. It is the single
gatekeeper: no privacy operation happens without going through it. It manages consent (with
non-revocable safety consents enforced), orchestrates the deletion lifecycle (create → dry-run →
confirm → execute), exposes the Memory Audit view, and runs integrity verification. All operations
are logged to the local audit trail. Stores are injected; everything runs on-device.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer12_privacy import integrity_verifier, memory_audit, selective_deletion
from backend.layer12_privacy.schemas import (
    _NON_REVOCABLE_CONSENTS,
    ConsentRecord,
    DeletionCertificate,
    DeletionRequest,
    DeletionScope,
)


class PrivacyAgent:
    def __init__(
        self, user_id: str, memory_store=None, semantic_store=None, identity_store=None,
        personality_store=None, longitudinal_store=None, safety_store=None, goal_store=None,
        audit_log: Optional[list] = None,
    ) -> None:
        self.user_id = user_id
        self.memory_store = memory_store
        self.semantic_store = semantic_store
        self.identity_store = identity_store
        self.personality_store = personality_store
        self.longitudinal_store = longitudinal_store
        self.safety_store = safety_store
        self.goal_store = goal_store
        self.audit_log = audit_log if audit_log is not None else []
        self._consents: dict[str, ConsentRecord] = {}

    # ── Consent (§7) ──────────────────────────────────────────────────────────
    def record_consent(
        self, consent_type: str, granted: bool, user_initiated: bool = True,
        now: Optional[datetime] = None,
    ) -> ConsentRecord:
        """Record a consent decision; safety-critical consents cannot be revoked (architecture doc §7)."""
        if not granted and consent_type in _NON_REVOCABLE_CONSENTS:
            raise ValueError(f"consent '{consent_type}' is non-revocable")
        now = now or datetime.utcnow()
        rec = ConsentRecord(
            user_id=self.user_id, consent_type=consent_type, granted=granted,
            granted_at=now if granted else None, revoked_at=None if granted else now,
            user_initiated=user_initiated)
        self._consents[consent_type] = rec
        return rec

    def is_consent_active(self, consent_type: str) -> bool:
        rec = self._consents.get(consent_type)
        return rec is not None and rec.granted

    # ── Deletion orchestration (§7) ───────────────────────────────────────────
    def request_deletion(
        self, deletion_type: str, scope: DeletionScope, now: Optional[datetime] = None,
    ) -> DeletionRequest:
        """Create a deletion request and run its dry-run cascade (architecture doc §4)."""
        req = selective_deletion.create_deletion_request(self.user_id, deletion_type, scope, now=now)
        selective_deletion.dry_run_deletion(
            req, self.memory_store, semantic_store=self.semantic_store,
            personality_store=self.personality_store, longitudinal_store=self.longitudinal_store)
        return req

    def execute_deletion(self, request: DeletionRequest, now: Optional[datetime] = None) -> DeletionCertificate:
        """Execute a confirmed deletion request, logging to the audit trail (architecture doc §4.3)."""
        return selective_deletion.execute_deletion(
            request, self.memory_store, audit_log=self.audit_log, now=now)

    # ── Audit + integrity (§7) ────────────────────────────────────────────────
    def generate_audit(self, now: Optional[datetime] = None):
        """Return the full Memory Audit view (architecture doc §5)."""
        return memory_audit.generate_audit_view(
            self.user_id, self.memory_store, semantic_store=self.semantic_store,
            identity_store=self.identity_store, safety_store=self.safety_store,
            goal_store=self.goal_store, now=now)

    def verify_integrity(self, records: list, stored_root: str, now: Optional[datetime] = None):
        """Run the daily Merkle integrity check (architecture doc §3.4)."""
        return integrity_verifier.run_check(records, stored_root, now=now)
