# Layer 10, Sub-Component: Retrospective Engine
#
# Responsibility: Generate retrospectives on demand or on schedule (1-week, 1-month, 1-year,
# milestone-anniversary retrospectives).
#
# Retrospective: "How have you grown in the past month? What were the big moments?
# What patterns do you notice?"
#
# Main functions:
#   - generate_retrospective(user_id, lookback_duration) -> RetrospectiveRecord
#   - generate_1_week_retrospective(user_id) -> RetrospectiveRecord
#   - generate_1_month_retrospective(user_id) -> RetrospectiveRecord
#   - generate_1_year_retrospective(user_id) -> RetrospectiveRecord
#   - generate_milestone_retrospective(milestone_id) -> RetrospectiveRecord
#
# Integration:
#   - Called on demand by user request or on schedule by background job
#   - Reads from Layer 2 (episodic memories, emotional history)
#   - Reads from Layer 7 (goal progress)
#   - Reads from Layer 10 (narrative arc, progress dimensions)
#   - Output delivered via Layer 9 (voice if enabled, text otherwise)
#
# Design: Retrospectives are reflective, not judgmental. They celebrate growth,
# acknowledge struggles, and help user see their own arc.
