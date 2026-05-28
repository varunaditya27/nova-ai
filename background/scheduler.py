# APScheduler Scheduler
#
# Responsibility: Register and manage all background jobs.
#
# Main function:
#   - start_scheduler(app: FastAPI) -> None
#   - Called from api/main.py lifespan.on_startup()
#
# Jobs registered:
#   - memory_consolidation_job (trigger: cron, interval: every 2 hours)
#   - pattern_detection_job (trigger: cron, interval: weekly)
#   - integrity_check_job (trigger: cron, interval: daily)
#   - longitudinal_summary_job (trigger: cron, interval: weekly, day: Sunday)
#   - proactive_check_job (trigger: interval, minutes: 30)
#
# Configuration read from config/defaults.yaml
