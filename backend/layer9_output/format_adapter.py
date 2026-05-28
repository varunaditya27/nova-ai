# Layer 9, Sub-Component: Format Adapter (SC-4)
#
# Responsibility: Decide format (register, markdown, emoji, length) for this specific response.
#
# Format Decision Matrix considers:
#   - Register: Formal ↔ Casual (based on mode, relationship stage, domain)
#   - Markdown: Which elements get markdown? (headers, bold, lists, code blocks)
#   - Emoji: None ↔ Occasional ↔ Frequent (per user preference + mode + circadian)
#   - Length: Short ↔ Medium ↔ Long (computed by length_calibrator)
#   - Punctuation: Serial commas? Ellipses? Question marks for curiosity?
#   - Line breaks: Dense prose ↔ Airy bulleted list
#
# Main functions:
#   - compute_format_spec(context, user_profile) -> FormatSpec
#   - should_use_markdown_for(element_type, context) -> bool
#   - compute_emoji_level(context, user_profile) -> EmojiLevel
#   - learn_format_preference(engagement_signal) -> None
#
# Integration:
#   - Called by Layer 4 (prompt_builder) to inform generation
#   - Reads from user_format_profile
#   - Reads from Layer 1 (circadian), Layer 5 (relationship), Layer 3 (emotion)
#   - Updates user_format_profile based on engagement signals
#
# Design: Format is not arbitrary—it's a channel for emotional information.
# Casual + emoji signals warmth. Formal + no emoji signals respect/boundaries.
