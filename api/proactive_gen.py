"""Layer-6 candidate generation for the live turn — the goal → proactive check-in handoff.

Pure (no I/O): turns a persisted Layer-7 ``Goal`` into a Layer-6 ``ProactiveItem`` when the goal has
an upcoming deadline or milestone, so the outreach queue (``GET /proactive``) actually accumulates
grounded candidates as the user forms goals. The item_id is derived from the goal id, so re-running
this every turn is idempotent (the store upserts by item_id — no duplicates).

Timezone-safe: goal dates may be naive or aware; everything is normalized to aware UTC before
comparison so the item's send/expiry windows stay consistent with the scheduler's aware ``now``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.layer6_proactivity.intake import on_goal_milestone_approaching
from backend.layer6_proactivity.schemas import ProactiveItem


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _nearest_future_target(goal, now: datetime):
    """The soonest upcoming (date, description) from the goal's unmet milestones or its deadline."""
    cands: list[tuple[datetime, str]] = []
    for ms in (getattr(goal, "milestones", None) or []):
        td = _as_utc(getattr(ms, "target_date", None))
        if td is not None and getattr(ms, "status", "pending") != "reached":
            cands.append((td, getattr(ms, "description", "") or getattr(ms, "title", "") or "milestone"))
    dl = _as_utc(getattr(goal, "deadline", None))
    if dl is not None:
        cands.append((dl, getattr(goal, "deadline_description", None) or "target deadline"))
    upcoming = sorted((c for c in cands if c[0] >= now), key=lambda c: c[0])
    return upcoming[0] if upcoming else None


def goal_checkin_item(goal, now: datetime) -> Optional[ProactiveItem]:
    """A deterministic GOAL_CHECK_IN for a goal with an upcoming deadline/milestone, else None."""
    now = _as_utc(now) or datetime.now(timezone.utc)
    target = _nearest_future_target(goal, now)
    if target is None:
        return None
    due, desc = target
    item = on_goal_milestone_approaching(
        goal_id=str(getattr(goal, "goal_id", "")),
        goal_title=getattr(goal, "title", "") or "your goal",
        milestone_description=desc, due_date=due, now=now)
    item.item_id = f"goalcheck-{getattr(goal, 'goal_id', '')}"   # deterministic → idempotent upsert
    return item
