import { describe, expect, it } from "vitest";
import { mergePages } from "@/lib/hooks/useMessages";
import type { MessageOut } from "@/lib/api/types";

function msg(cursor: number, content: string): MessageOut {
  return {
    message_id: `m${cursor}`,
    cursor,
    role: "user",
    content,
    created_at: null,
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

describe("mergePages", () => {
  it("flattens newest-first pages into one ascending, deduped list", () => {
    // Each page arrives newest-first (getMessages); we page BACK for older turns.
    const page1 = [msg(5, "e"), msg(4, "d"), msg(3, "c")];
    const page2 = [msg(3, "c"), msg(2, "b"), msg(1, "a")]; // overlaps at cursor 3
    const merged = mergePages([page1, page2]);
    expect(merged.map((m) => m.cursor)).toEqual([1, 2, 3, 4, 5]);
    expect(merged).toHaveLength(5);
  });

  it("returns an empty list for no pages", () => {
    expect(mergePages([])).toEqual([]);
  });
});
