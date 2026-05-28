# Calendar Plugin
#
# Integrates with Google Calendar, Apple Calendar, or Outlook.
# Provides unified interface via CalendarAdapter abstraction.
#
# Actions:
#   - create_event(title, time, duration, description) -> EventID
#   - list_events(date_range) -> list[Event]
#   - delete_event(event_id) -> bool
#   - find_free_time(duration, date_range) -> list[TimeSlot]
#
# Implementation notes:
#   - Uses OAuth2 for authentication
#   - Credentials stored securely in Layer 12 keystore
#   - Read-only operations are AUTO confirmation tier
#   - Create is SOFT; delete is HARD
#   - Undo support: reversible for all operations (deletes stored as archived, not removed)
