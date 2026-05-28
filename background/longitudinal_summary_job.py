# Longitudinal Summary Job
#
# Responsibility: Generate weekly summaries for all active users.
#
# Trigger: Weekly (configurable day/time, typically Sunday 1 AM)
#
# Executes:
#   - layer10_longitudinal.weekly_summary.generate_weekly_summary() for all users
#   - Updates narrative arc, progress dimensions
#   - Generates retrospectives if milestone reached
#
# Performance: Typically 1-5 minutes depending on number of active users
