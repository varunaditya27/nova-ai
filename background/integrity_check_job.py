"""Integrity check job — verify the tamper-evident hash chains (Layer-2 audit + Layer-11 safety
record + Layer-12 privacy).

Runs daily. Deterministic and dependency-free beyond the stores; returns a status dict that the
scheduler logs and the manual-trigger endpoint returns.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.audit_trail import PostgresAuditTrail
    from infra.db.privacy_audit import PostgresPrivacyAudit
    from infra.db.safety_record_store import PostgresSafetyRecordStore

    uid = app_state.default_user_id
    audit_ok = PostgresAuditTrail(app_state.session_factory, uid).verify()
    privacy_ok = PostgresPrivacyAudit(app_state.session_factory, uid).verify()
    safety_ok = PostgresSafetyRecordStore(app_state.session_factory, uid).verify_chain()
    status = "INTACT" if (audit_ok and privacy_ok and safety_ok) else "TAMPER_DETECTED"
    if status != "INTACT":
        logger.error("integrity check FAILED: audit_ok=%s privacy_ok=%s safety_ok=%s",
                     audit_ok, privacy_ok, safety_ok)
    return {"status": status, "audit_chain_ok": audit_ok, "privacy_chain_ok": privacy_ok,
            "safety_chain_ok": safety_ok}
