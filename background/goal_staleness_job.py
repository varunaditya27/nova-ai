"""Goal staleness sweep — Layer-7 SC-2 silent-neglect decay (architecture doc §5.6).

Runs weekly. `progress_monitor.run_staleness_scan` had zero production callers -- a goal only
ever reached a terminal/at-risk status through an explicit completion/abandonment phrase in a
live turn (`backend/pipeline/conversation_orchestrator.py` via `run_goal_pipeline`); silent
neglect (the user just stops mentioning a goal) never decayed it. This job is the missing
caller, same `run(app_state) -> dict` shape as `pattern_detection_job.py`.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")

_SCANNED_STATUSES = ["tentative", "active", "on_track", "at_risk"]


def run(app_state) -> dict:
    from datetime import datetime, timezone
    from infra.db.goal_store import PostgresGoalStore
    from backend.layer7_goals.progress_monitor import run_staleness_scan

    uid = app_state.default_user_id
    now = datetime.now(timezone.utc)
    store = PostgresGoalStore(app_state.session_factory, uid)
    goals = store.load_by_status(_SCANNED_STATUSES)
    changes = run_staleness_scan(goals, now=now)

    by_id = {g.goal_id: g for g in goals}
    for change in changes:
        goal = by_id.get(change.goal_id)
        if goal is None:
            continue
        goal.status = change.new_status
        goal.status_changed_at = now
        store.update_goal(goal)

    logger.info("goal staleness scan: scanned=%d changed=%d", len(goals), len(changes))
    return {"scanned": len(goals), "changed": len(changes),
            "changes": [{"goal_id": c.goal_id, "new_status": c.new_status, "reason": c.reason}
                       for c in changes]}
