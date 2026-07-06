"""Integrity check job — verify the tamper-evident hash chains (Layer-2 audit + Layer-12 privacy).

Runs daily. Deterministic and dependency-free beyond the stores; returns a status dict that the
scheduler logs and the manual-trigger endpoint returns.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.audit_trail import PostgresAuditTrail
    from infra.db.privacy_audit import PostgresPrivacyAudit

    uid = app_state.default_user_id
    audit_ok = PostgresAuditTrail(app_state.session_factory, uid).verify()
    privacy_ok = PostgresPrivacyAudit(app_state.session_factory, uid).verify()
    status = "INTACT" if (audit_ok and privacy_ok) else "TAMPER_DETECTED"
    if status != "INTACT":
        logger.error("integrity check FAILED: audit_ok=%s privacy_ok=%s", audit_ok, privacy_ok)
    return {"status": status, "audit_chain_ok": audit_ok, "privacy_chain_ok": privacy_ok}
