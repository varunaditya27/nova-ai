import { describe, expect, it } from "vitest";
import { buildDays, mondayOffset, monthRange, quiltTone } from "@/lib/calendar";

describe("buildDays", () => {
  it("enumerates an inclusive UTC day range with counts and weekdays", () => {
    const days = buildDays("2026-07-06T00:00:00Z", "2026-07-08T12:00:00Z", {
      "2026-07-07": 9,
    });
    expect(days.map((d) => d.date)).toEqual([
      "2026-07-06",
      "2026-07-07",
      "2026-07-08",
    ]);
    expect(days.find((d) => d.date === "2026-07-07")?.count).toBe(9);
    expect(days.find((d) => d.date === "2026-07-08")?.count).toBe(0);
    expect(days[0].dow).toBe(1); // 2026-07-06 is a Monday
  });
});

describe("monthRange / mondayOffset", () => {
  it("spans the whole UTC month", () => {
    const r = monthRange(2026, 1); // February 2026
    expect(r.start.startsWith("2026-02-01")).toBe(true);
    expect(r.end.startsWith("2026-02-28")).toBe(true);
  });
  it("starts the week on Monday", () => {
    expect(mondayOffset(1)).toBe(0); // Monday
    expect(mondayOffset(0)).toBe(6); // Sunday is the last column
  });
});

describe("quiltTone", () => {
  it("leaves empty days flat and deepens busy ones, flipping the text when needed", () => {
    expect(quiltTone(0, 10).background).toBe("var(--sunk)");
    expect(quiltTone(1, 10).color).toBe("var(--ink)");
    expect(quiltTone(10, 10).color).toBe("var(--accent-ink)");
    expect(quiltTone(10, 10).background).toContain("100%");
  });
});
