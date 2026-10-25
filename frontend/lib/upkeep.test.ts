import { describe, expect, it } from "vitest";
import { CHORES, describeResult } from "./upkeep";

describe("upkeep copy", () => {
  it("covers every backend job with a plain title", () => {
    expect(CHORES).toHaveLength(11);
    for (const c of CHORES) expect(c.title).not.toMatch(/[_]/);
  });
  it("turns raw results into readable rows", () => {
    expect(describeResult({ swept: 12, semantic_memories_created: 2, new_semantic_summaries: [] })).toEqual([
      { label: "Memories reviewed", value: "12" },
      { label: "Lessons written down", value: "2" },
    ]);
    expect(describeResult({ skipped: "cold_start_active" })[0].value).toContain("getting to know you");
    expect(describeResult({ status: "INTACT", audit_chain_ok: true })[0].value).toContain("nothing was altered");
    expect(describeResult({ some_new_thing: true })[0]).toEqual({ label: "Some new thing", value: "Yes" });
  });
});
