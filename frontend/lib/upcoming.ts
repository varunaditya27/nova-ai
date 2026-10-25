import type { Goal } from "@/lib/api/types";
import { dayDiff } from "@/lib/time";

export type Upcoming = {
  key: string;
  goalId: string;
  goalTitle: string;
  /** What is due: the milestone's name, or the goal's own deadline wording. */
  what: string;
  date: string;
  kind: "milestone" | "deadline";
};

/** Everything coming due within `horizonDays` (and anything recently overdue), soonest first. */
export function upcoming(
  goals: Goal[],
  now: Date = new Date(),
  horizonDays = 30,
): Upcoming[] {
  const out: Upcoming[] = [];
  for (const g of goals) {
    if (g.status === "completed" || g.status === "abandoned") continue;
    for (const m of g.milestones) {
      if (m.status === "reached" || !m.target_date) continue;
      out.push({
        key: `${g.goal_id}-m-${m.title}`,
        goalId: g.goal_id,
        goalTitle: g.title,
        what: m.title,
        date: m.target_date,
        kind: "milestone",
      });
    }
    if (g.deadline) {
      out.push({
        key: `${g.goal_id}-d`,
        goalId: g.goal_id,
        goalTitle: g.title,
        what: g.deadline_description || "The date you set",
        date: g.deadline,
        kind: "deadline",
      });
    }
  }
  return out
    .filter((u) => {
      const d = dayDiff(new Date(u.date), now);
      return d <= horizonDays && d >= -14;
    })
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}
