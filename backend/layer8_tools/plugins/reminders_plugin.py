# Reminders Plugin
#
# Create and retrieve reminders (lightweight timeline management).
# Not a full task manager—just simple reminder creation.
#
# Actions:
#   - create_reminder(text, datetime, recurrence=None) -> ReminderID
#   - list_reminders(date_range) -> list[Reminder]
#   - dismiss_reminder(reminder_id) -> None
#   - snooze_reminder(reminder_id, duration) -> None
#   - delete_reminder(reminder_id) -> bool
#
# Implementation notes:
#   - Backed by system reminders (iOS, Android, OS-level)
#   - Or stored in Layer 7 goals / Layer 6 proactivity as appropriate
#   - AUTO confirmation tier
#   - Full undo support
