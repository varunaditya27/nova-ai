# Layer 9, Sub-Component: Thinking Pause
#
# Responsibility: Insert a pause before responding to indicate "thinking."
#
# Pause duration = f(complexity, emotional_intensity, circadian)
#
# Base formula:
#   system1_base: 400ms (quick System 1 responses)
#   system2_base: 1200ms (full System 2 reasoning)
#   high_complexity_bonus: +600ms if reasoning about difficult topic
#   high_emotion_bonus: +400ms if emotional intensity > 0.7
#   circadian_multiplier: ×1.3 if late_night (slower, more careful)
#
# Example:
#   - Casual System 1 message, afternoon: 400ms
#   - Emotional System 2 message, late night: (1200 + 600 + 400) × 1.3 = ~2860ms
#
# Main functions:
#   - compute_pause_duration(context) -> int  # milliseconds
#   - should_show_thinking_indicator(context) -> bool
#
# Integration:
#   - Called by interaction_orchestrator before streaming response
#   - Emits ThinkingEvent to frontend for visual "thinking..." indicator
#   - No server-side latency (pause happens client-side)
#
# Design: Thinking pause makes responses feel more natural—Nova is not just spitting text instantly.
