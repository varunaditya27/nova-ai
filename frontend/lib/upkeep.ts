export type Chore = { name: string; title: string; what: string; when: string };

/** Nova's background housekeeping, in plain words. `name` is the backend job id. */
export const CHORES: Chore[] = [
  { name: "memory_consolidation", title: "Tidy memories", what: "Lets small details fade, merges similar memories, and writes down what stays true about you.", when: "Every couple of hours" },
  { name: "proactive_check", title: "Decide what to bring up", what: "Works out whether there’s something worth reaching out about, and when.", when: "Every half hour" },
  { name: "longitudinal_summary", title: "Write this week’s chapter", what: "Writes up the week as a short chapter for Our story.", when: "Weekly" },
  { name: "narrative_arc", title: "Update the story so far", what: "Rebuilds the current chapter of your life from what has happened.", when: "Weekly" },
  { name: "pattern_detection", title: "Spot patterns in your days", what: "Looks for things that keep repeating — when you’re stressed, what helps.", when: "Weekly" },
  { name: "social_pattern_detection", title: "Spot patterns with your people", what: "Looks for repeating themes in your relationships.", when: "Weekly" },
  { name: "goal_staleness", title: "Check on stalled goals", what: "Notices goals you haven’t mentioned in a while and marks them as slipping.", when: "Weekly" },
  { name: "dependency_monitor", title: "Check the balance", what: "Makes sure Nova is a help in your life rather than something you lean on too heavily.", when: "Weekly" },
  { name: "life_calendar", title: "Update milestones and look-backs", what: "Marks anniversaries and moments, and writes look-backs when they come due.", when: "Daily" },
  { name: "distress_gap", title: "Check in after hard days", what: "If you had a rough patch and then went quiet, queues a gentle check-in.", when: "Daily" },
  { name: "integrity_check", title: "Verify nothing was altered", what: "Checks that Nova’s records haven’t been tampered with.", when: "Daily" },
];

const LABELS: Record<string, string> = {
  swept: "Memories reviewed",
  deleted: "Faded away",
  archived: "Set aside",
  clusters_detected: "Themes found",
  semantic_memories_created: "Lessons written down",
  episodes_consolidated: "Memories merged",
  episodes: "Memories looked at",
  sessions: "Conversations looked at",
  patterns: "Patterns found",
  new_patterns: "New patterns",
  nodes: "People considered",
  events: "Events looked at",
  chapters: "Chapters",
  life_events: "Life events found",
  entries: "Dates tracked",
  fired: "Dates that came due",
  retrospectives: "Look-backs written",
  scanned: "Goals checked",
  changed: "Goals updated",
  episodes_scanned: "Memories checked",
  queued: "Check-in queued",
  score: "Reliance level",
  trend: "Direction",
  tier: "Overall",
};

const SKIPS: Record<string, string> = {
  cold_start_active: "Skipped — Nova is still getting to know you, so it stays quiet for now.",
};

const HIDDEN = new Set(["summary_id", "new_semantic_summaries", "changes", "dominant_signals"]);

function plainValue(key: string, v: unknown): string {
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (key === "tier" && typeof v === "string") return v === "healthy" ? "Healthy" : v.replace(/_/g, " ");
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  return String(v).replace(/_/g, " ");
}

/** A job's raw result as plain rows. Unknown keys are tidied, never shown as code. */
export function describeResult(result: Record<string, unknown>): { label: string; value: string }[] {
  if (typeof result.skipped === "string") return [{ label: "Result", value: SKIPS[result.skipped] ?? `Skipped — ${result.skipped.replace(/_/g, " ")}.` }];
  if (typeof result.status === "string") {
    const ok = result.status === "INTACT";
    return [{ label: "Result", value: ok ? "Everything checks out — nothing was altered." : "Something doesn’t add up. Open Privacy to look closer." }];
  }
  return Object.entries(result)
    .filter(([k, v]) => !HIDDEN.has(k) && v !== null && typeof v !== "object")
    .map(([k, v]) => ({
      label: LABELS[k] ?? k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()),
      value: plainValue(k, v),
    }));
}
