"""In-process background scheduler (APScheduler), opt-in via ``config['scheduler']['enabled']``.

The six jobs are plain ``run(app_state) -> dict`` callables (directly testable, no scheduler
needed). ``start_scheduler`` lazily imports APScheduler so importing this module never requires it
(the offline test gate runs on a bare interpreter); if APScheduler is missing or the config flag is
off, it is a logged no-op. ``run_job`` executes one job by name (used by the manual-trigger route).
"""
from __future__ import annotations

import logging

from background import (
    dependency_monitor_job,
    integrity_check_job,
    longitudinal_summary_job,
    memory_consolidation_job,
    pattern_detection_job,
    proactive_check_job,
)

logger = logging.getLogger("nova.jobs")

JOBS = {
    "memory_consolidation": memory_consolidation_job.run,
    "proactive_check": proactive_check_job.run,
    "pattern_detection": pattern_detection_job.run,
    "integrity_check": integrity_check_job.run,
    "longitudinal_summary": longitudinal_summary_job.run,
    "dependency_monitor": dependency_monitor_job.run,
}


def run_job(app_state, name: str) -> dict:
    """Run one job by name. Raises KeyError for an unknown job."""
    return JOBS[name](app_state)


def start_scheduler(app_state):
    """Start the APScheduler with the configured cadences. No-op if disabled or APScheduler absent.
    Returns the started scheduler (or None)."""
    cfg = (getattr(app_state, "config", {}) or {}).get("scheduler", {})
    if not cfg.get("enabled", False):
        logger.info("scheduler disabled (config.scheduler.enabled=false)")
        return None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception:
        logger.warning("APScheduler not installed; background jobs will not run")
        return None

    sched = BackgroundScheduler(daemon=True)

    def _wrap(name):
        def _job():
            try:
                result = JOBS[name](app_state)
                logger.info("job %s -> %s", name, result)
            except Exception:
                logger.exception("job %s failed", name)
        return _job

    sched.add_job(_wrap("memory_consolidation"), "interval",
                  hours=cfg.get("memory_consolidation_hours", 2), id="memory_consolidation")
    sched.add_job(_wrap("proactive_check"), "interval",
                  minutes=cfg.get("proactive_check_minutes", 30), id="proactive_check")
    sched.add_job(_wrap("integrity_check"), "interval",
                  hours=cfg.get("integrity_check_hours", 24), id="integrity_check")
    sched.add_job(_wrap("pattern_detection"), "interval",
                  days=cfg.get("pattern_detection_days", 7), id="pattern_detection")
    sched.add_job(_wrap("longitudinal_summary"), "interval",
                  days=cfg.get("longitudinal_summary_days", 7), id="longitudinal_summary")
    sched.add_job(_wrap("dependency_monitor"), "interval",
                  days=cfg.get("dependency_monitor_days", 7), id="dependency_monitor")
    sched.start()
    logger.info("scheduler started with %d jobs", len(JOBS))
    return sched
