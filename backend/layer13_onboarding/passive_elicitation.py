# Layer 13, Sub-Component: Passive Elicitation
#
# Responsibility: Silent context extraction from message signals without asking.
#
# Observes:
#   - Vocabulary complexity (education level, language preference)
#   - Sentence structure (analytical vs. conversational)
#   - Emoji usage (personality hint)
#   - Time of messaging (timezone, sleep schedule)
#   - Topic choices in first messages (interests, concerns)
#   - Emotional register (formal, casual, vulnerable)
#
# Main functions:
#   - extract_context_silently(message, metadata) -> InferredContext
#   - update_user_profile_from_signals(inferred_context) -> None
#   - compute_confidence(inferred_fact) -> float  # 0–1
#
# Integration:
#   - Runs on every message during cold start
#   - Reads from Layer 1 (temporal signals), message text/metadata
#   - Updates user profile without user knowledge
#   - No LLM calls; purely algorithmic
#
# Design: Passive elicitation is learning, not interrogation.
# User doesn't feel surveyed or profiled.
