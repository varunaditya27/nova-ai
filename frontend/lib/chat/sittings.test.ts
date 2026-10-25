import { describe, expect, it } from "vitest";
import { groupSittings, passageOfTime } from "./sittings";
import type { MessageOut } from "@/lib/api/types";

const DAY = 86_400_000;
const NOW = new Date("2026-10-25T20:00:00");

function msg(id: string, session: string, at: Date, role: "user" | "nova" = "user"): MessageOut {
  return {
    message_id: id,
    cursor: Number(id.replace(/\D/g, "")) || 0,
    role,
    content: id,
    created_at: at.toISOString(),
    session_key: session,
    conversation_mode: null,
    crisis_active: false,
    tool_invoked: false,
    echoes: [],
    bookmarked: false,
    bookmark_category: null,
    is_milestone: false,
    milestone_label: null,
  };
}

describe("passageOfTime", () => {
  it("ignores ordinary gaps and names long silences in words", () => {
    expect(passageOfTime(2 * DAY)).toBeNull();
    expect(passageOfTime(4 * DAY)).toBe("4 days pass.");
    expect(passageOfTime(8 * DAY)).toBe("A week passes.");
    expect(passageOfTime(21 * DAY)).toBe("3 weeks pass.");
    expect(passageOfTime(95 * DAY)).toBe("3 months pass.");
    expect(passageOfTime(400 * DAY)).toBe("A year passes.");
  });
});

describe("groupSittings", () => {
  it("starts a new sitting when the session changes and marks long silences", () => {
    const t0 = new Date(NOW.getTime() - 12 * DAY);
    const sittings = groupSittings(
      [
        msg("m1", "a", t0),
        msg("m2", "a", new Date(t0.getTime() + 60_000), "nova"),
        msg("m3", "b", new Date(NOW.getTime() - 60_000)),
      ],
      NOW
    );
    expect(sittings).toHaveLength(2);
    expect(sittings[0].messages.map((m) => m.message_id)).toEqual(["m1", "m2"]);
    expect(sittings[0].passage).toBeNull();
    expect(sittings[1].passage).toBe("A week passes.");
    expect(sittings[1].heading).toBe("This evening");
  });

  it("returns nothing for an empty thread", () => {
    expect(groupSittings([], NOW)).toEqual([]);
  });
});
