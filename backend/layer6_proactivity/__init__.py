# Layer 6 — Proactive Engagement Engine
#
# Core distinction: This is the FIRST layer that operates WITHOUT user initiation.
# Every other layer is reactive—runs when the user sends a message.
# Layer 6 is proactive—reaches out first.
#
# Central question: When should Nova initiate contact, and what should it say?
#
# Critical design principle: Default overwhelmingly to silence.
# Only speak when signal is strong, timing is right, and content is grounded in something real.
#
# Failure mode if done wrong: Unsolicited messages that feel algorithmically timed,
# emotionally tone-deaf, or attention-extracting destroy trust faster than any bad response.
#
# Main components:
#   - check_in_engine.py: Trigger evaluation + intrusion cost function
#   - pattern_detector.py: Temporal-emotional cycle detection across sessions
#   - anticipatory_assistant.py: Pre/post event prep, cyclical anticipation
#   - notification_policy.py: DND gates, timing constraints, batching, user response learning
#   - schemas.py: CheckInTrigger, PatternObject, NotificationEvent, IntrusionScore
#
# Execution model: SC-1 runs background (~30min poll). SC-2-5 deterministic.
# Layer 6 operates independently of user-initiated conversation pipeline.
