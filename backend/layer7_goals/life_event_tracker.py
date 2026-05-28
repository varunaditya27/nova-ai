# Layer 7, Sub-Component: Life Event Tracker
#
# Responsibility: Detect significant life events and cascade their impact across system.
#
# Life events: Job change, relationship milestone, health change, location move, loss, achievement.
#
# Cascade logic:
#   - Life event detected → Updates User World Model (Layer 2)
#   - Affects goals: May activate/pause/complete related goals
#   - Affects relationships: May trigger relationship updates (Layer 5)
#   - Affects emotional baseline: May shift recent emotional trajectory (Layer 3)
#   - Affects future proactivity: May trigger check-ins or compassionate outreach (Layer 6)
#
# Main functions:
#   - detect_life_events(user_message, context) -> list[LifeEvent]
#   - process_life_event(event: LifeEvent) -> None
#   - cascade_event_effects(event: LifeEvent) -> CascadeResult
#   - get_recent_life_events(user_id, days_lookback=90) -> list[LifeEvent]
#
# Integration:
#   - Called post-session via state_updater
#   - May call LLM to classify event type and significance
#   - Updates across Layer 2 (memory), Layer 5 (relationships), Layer 7 (goals)
#   - Integrates with Layer 6 (proactivity)
#
# Design: Life events are major inflection points. They ripple through the whole system.
