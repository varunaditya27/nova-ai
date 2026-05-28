# Layer 13 — Onboarding & Cold Start Architecture
#
# Core challenge: The cold start problem in AI companions is uniquely high-stakes.
# The first session shapes whether a person ever trusts Nova enough to let it become
# what it's capable of being.
#
# Layer 13 manages the entire onboarding arc from first message to graduation.
# It's not just the first impression. It's the system that enables the system to initialize.
#
# Three design principles (non-negotiable):
#   1. Earn before asking: Don't interrogate. Let Nova demonstrate value first.
#   2. Infer before asking: Read signals, observe, then ask.
#   3. Delay features, not presence: Feel complete from message one while machinery starts.
#
# Main components:
#   - cold_start_engine.py: Orchestrator—active from T=0 until graduation
#   - passive_elicitation.py: Silent context extraction from message signals
#   - active_elicitation_queue.py: Prioritized queue of naturally-triggered questions
#   - context_constructor.py: Accelerated first-session context building
#   - graduation_evaluator.py: Evaluates graduation criteria
#   - feature_pacing.py: Controls capability unlock schedule
#   - schemas.py: ColdStartState, ElicitationItem, FeatureReadinessProfile, GraduationReport
#
# Execution model: Cold start engine overlays normal pipeline. Adds constraints and
# context-building. Self-terminates on graduation.
