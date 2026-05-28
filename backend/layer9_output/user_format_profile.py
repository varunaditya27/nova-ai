# Layer 9, Sub-Component: User Format Profile
#
# Responsibility: Track and learn per-user format preferences from engagement signals.
#
# Signals:
#   - Message length ratio: If user's responses are short, they prefer concise output
#   - Emoji response: Does user use emoji in their messages? Do they react with emoji to Nova's?
#   - Markdown engagement: Do they click on / expand sections? Do they read lists?
#   - Formality of speech: User's register can inform Nova's register
#
# Main functions:
#   - get_learned_preference(user_id, dimension) -> Preference
#   - update_from_engagement(user_id, engagement_signal) -> None
#   - initialize_defaults(user_id) -> UserFormatProfile
#
# Integration:
#   - Written to by format_adapter after each response
#   - Read by format_adapter at start of format computation
#   - Stored in infra.db.models.output_prefs.UserFormatProfile
#
# Design: Format preferences are learned, not set. They evolve as you use Nova.
