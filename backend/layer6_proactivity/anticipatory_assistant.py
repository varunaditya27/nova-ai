# Layer 6, Sub-Component: Anticipatory Assistant
#
# Responsibility: Generate proactive messages in anticipation of known events or patterns.
#
# Examples:
#   - "I know you have that presentation tomorrow. How are you feeling about it?"
#   - "It's been a hard week. Weekend's almost here."
#   - "You mentioned trying to cut back on caffeine. How's that going?"
#
# Main functions:
#   - generate_anticipatory_prompt(event_type, event_context) -> str
#   - generate_check_in_message(pattern: PatternObject) -> str
#   - generate_milestone_message(milestone_type, goal_context) -> str
#   - generate_coaching_message(coaching_opportunity) -> str
#
# Integration:
#   - Called only after check_in_engine and notification_policy clear an item for delivery
#   - Calls infra.llm.groq_client (one LLM call per proactive message)
#   - Output passed to Layer 9 (Output Delivery)
#
# Design: All anticipatory messages are grounded in real user data (mentioned events, goals, patterns).
# No generic platitudes. Every message has a reason and can be explained.
