# Layer 11, Sub-Component: Safe Mode Enforcer
#
# Responsibility: Hard override—when crisis mode is active, suppress normal embellishments.
#
# Safe mode disables:
#   - All micro-interactions (backchannels, thinking pauses, self-edits)
#   - Emoji, markdown, fancy formatting
#   - Voice/audio output (text only)
#   - Proactive outreach (Layer 6 blocked)
#
# Safe mode response is:
#   - Plain prose (no markdown)
#   - Direct, warm, non-clinical
#   - Clear and unambiguous
#   - Focused on presence and support
#   - Free from embellishment
#
# Main functions:
#   - enforce_safe_mode(response_text, crisis_level) -> SafeModeResponse
#   - strip_micro_interactions(text) -> str
#   - apply_crisis_tone(text) -> str
#
# Integration:
#   - Called by Layer 9 (Output Delivery) when crisis_mode_active = True
#   - Runs post-generation (never blocks LLM)
#   - Returns modified response before sending to user
#
# Design: Safe mode response is still Nova—just stripped of anything that might
# feel dismissive, scattered, or inauthentic during crisis.
