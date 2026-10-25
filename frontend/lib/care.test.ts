import { describe, expect, it } from "vitest";
import { describeCheckIn, worthShowing } from "./care";

describe("care copy", () => {
  it("describes each level of concern in human words and hides the rest", () => {
    expect(describeCheckIn("tier_1")).toContain("very heavy");
    expect(describeCheckIn("tier_3")).toContain("gentle eye");
    expect(describeCheckIn("none")).toBe("");
    const events = [
      { tier: "tier_2", confidence: 1, detected_at: null, signal_types: [] },
      { tier: "none", confidence: 0, detected_at: null, signal_types: [] },
    ];
    expect(worthShowing(events)).toHaveLength(1);
  });
});
