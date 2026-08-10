"""Duck-type store adapters Layer 12's privacy routes need (architecture doc §5.2, §5.5).

Each wraps a Postgres store to the narrow interface a `backend/layer12_privacy/` function
expects, so the layer's real logic never has to know about SQLAlchemy models.
"""
from __future__ import annotations


class EpisodicDeletionStore:
    """Adapts PostgresMemoryStore to the get/update/delete/all duck-type Layer-12 deletion expects."""
    def __init__(self, store, user_id):
        self._s, self._u = store, user_id
    def all(self):
        return self._s.active_episodic(self._u)
    def get(self, mid):
        return self._s.get_episodic(mid)
    def update(self, mid, fields):
        self._s.update_episodic(mid, fields)
    def delete(self, mid):
        self._s.delete_episodic(mid)


class SemanticDeletionStore:
    """Adapts PostgresMemoryStore to the duck-type dry_run_deletion/redact_cascade's semantic-facts
    cascade check expects (`.all()`, and `.get()`/`.update()` for real redaction)."""
    def __init__(self, store, user_id):
        self._s, self._u = store, user_id
    def all(self):
        return self._s.active_semantic(self._u)
    def get(self, mid):
        return self._s.get_semantic(mid)
    def update(self, mid, fields):
        self._s.update_semantic(mid, fields)


class LongitudinalDeletionStore:
    """Adapts PostgresLongitudinalStore to the duck-type dry_run_deletion/redact_cascade's
    longitudinal cascade check expects (`.all_weekly_summaries()`, and `.get()`/`.update()` for
    real redaction)."""
    def __init__(self, store):
        self._s = store
    def all_weekly_summaries(self):
        return self._s.summaries(period="weekly")
    def get(self, summary_id):
        return next((s for s in self._s.summaries(period="weekly") if s.summary_id == summary_id),
                    None)
    def update(self, summary):
        self._s.save_summary(summary, period="weekly")


class IdentityAuditStore:
    """Adapts PostgresMemoryStore to the `.all()` duck-type generate_audit_view's identity-beliefs
    read expects."""
    def __init__(self, store):
        self._s = store
    def all(self):
        return self._s.identity_beliefs()


class SafetyAuditStore:
    """Adapts PostgresSafetyLog to the `.crisis_session_count()` duck-type generate_audit_view
    expects."""
    def __init__(self, store, user_id):
        self._s, self._u = store, user_id
    def crisis_session_count(self):
        return self._s.crisis_count(self._u)


class GoalAuditStore:
    """Adapts PostgresGoalStore to the `.active_goal_count()` duck-type generate_audit_view
    expects."""
    def __init__(self, store):
        self._s = store
    def active_goal_count(self):
        return len(self._s.load_by_status(["active"]))
