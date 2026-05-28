# Background Jobs & Scheduler
#
# APScheduler-based background task orchestration.
#
# Jobs:
#   - memory_consolidation_job.py: Runs forgetting engine every N sessions
#   - pattern_detection_job.py: Weekly pattern detection sweep
#   - integrity_check_job.py: Daily data integrity verification
#   - longitudinal_summary_job.py: Weekly summary generation
#   - proactive_check_job.py: Periodic check-in evaluation (~30 min)
#
# Main component:
#   - scheduler.py: Registers all jobs, manages lifecycle
