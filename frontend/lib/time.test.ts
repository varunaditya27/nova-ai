import { describe, expect, it } from "vitest";
import { relativeTime } from "@/lib/time";

describe("relativeTime", () => {
  it("returns an empty string for null or unparseable input", () => {
    expect(relativeTime(null)).toBe("");
    expect(relativeTime("not-a-date")).toBe("");
  });

  it("describes the past in human units", () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 86_400_000).toISOString();
    expect(relativeTime(twoDaysAgo)).toBe("2 days ago");
  });

  it("collapses very recent times to a minute-grained phrase", () => {
    const justNow = new Date(Date.now() - 5_000).toISOString();
    // numeric:auto renders 0 minutes as "this minute"
    expect(relativeTime(justNow)).toMatch(/this minute|minute/);
  });
});
