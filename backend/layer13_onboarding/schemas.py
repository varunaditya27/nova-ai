# Schemas for Layer 13 — Onboarding & Cold Start Architecture
#
# Defines cold start state, elicitation queue, and graduation criteria.
#
# Key schemas:
#   - ColdStartState: Current cold start phase (active, paused, graduated)
#   - ElicitationItem: A question to ask (priority, asked_count, responses_received)
#   - ElicitationQueue: Prioritized queue of elicitation items
#   - FeatureReadinessProfile: Which features are unlocked (goals? relationships? proactivity?)
#   - GraduationCriteria: Conditions for cold start to end
#   - GraduationReport: Summary of what was learned during cold start
#
# Design: All cold start structures are temporary (exist only during cold start).
# After graduation, cold start state is archived and main system takes over.
