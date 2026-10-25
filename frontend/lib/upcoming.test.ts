import { describe, expect, it } from "vitest";
import { upcoming } from "./upcoming";
import type { Goal } from "@/lib/api/types";

const NOW = new Date("2026-10-25T10:00:00");
const iso = (days: number) =>
  new Date(NOW.getTime() + days * 86_400_000).toISOString();

function goal(over: Partial<Goal>): Goal {
  return {
    goal_id: "g1",
    title: "Finish DSA",
    status: "active",
    progress_score: 0,
    description: "",
    deadline: null,
    deadline_description: null,
    milestones: [],
    habits: [],
    ...over,
  };
}

describe("upcoming", () => {
  it("lists soon-due milestones and deadlines, soonest first, skipping reached and far-off ones", () => {
    const items = upcoming(
      [
        goal({
          deadline: iso(20),
          deadline_description: "by mid-November",
          milestones: [
            { title: "Trees", target_date: iso(5), status: "pending" },
            { title: "Graphs", target_date: iso(90), status: "pending" },
            { title: "Arrays", target_date: iso(2), status: "reached" },
          ],
        }),
      ],
      NOW,
    );
    expect(items.map((i) => i.what)).toEqual(["Trees", "by mid-November"]);
  });

  it("keeps recently overdue items but not finished goals", () => {
    expect(upcoming([goal({ deadline: iso(-3) })], NOW)).toHaveLength(1);
    expect(
      upcoming([goal({ deadline: iso(3), status: "completed" })], NOW),
    ).toHaveLength(0);
  });
});
