# Test: Length Calibrator
#
# Tests:
#   - Calibrate response length to user preferences
#   - Short: ~40 tokens, Medium: ~80 tokens, Long: ~220 tokens
#   - Truncate long responses gracefully (keep semantic meaning)
#   - Expand short responses (add supporting details)
#   - Preserve tone (don't change voice when adjusting length)
#
# Fixtures: sample_response, user_format_profile
