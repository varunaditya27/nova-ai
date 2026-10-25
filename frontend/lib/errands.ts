/** Plain names for Nova's tools — the UI never shows `web_search` or `create_reminder`. */
const TOOL_NAMES: Record<string, string> = {
  calendar: "Calendar",
  reminders: "Reminder",
  email: "Email",
  notes: "Note",
  web_search: "Web search",
};

export function toolName(tool: string): string {
  return TOOL_NAMES[tool] ?? tool.replace(/_/g, " ");
}

const OPERATIONS: Record<string, string> = {
  create_reminder: "set a reminder",
  complete_reminder: "mark a reminder done",
  create_event: "add an event",
  delete_event: "remove an event",
  find_free_time: "look for free time",
  draft: "draft an email",
  send: "send an email",
  create_note: "write a note",
  search: "search the web",
};

/** "set a reminder", "draft an email" — what Nova did, as a verb phrase. */
export function operationPhrase(operation: string): string {
  return OPERATIONS[operation] ?? operation.replace(/_/g, " ");
}

export function outcomeWords(outcome: string, undone: boolean): string {
  if (undone) return "Undone";
  if (outcome === "success" || outcome === "ok") return "Done";
  if (outcome === "failed" || outcome === "error") return "Didn’t work";
  return outcome.replace(/_/g, " ");
}
