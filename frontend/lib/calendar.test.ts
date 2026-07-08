import { describe, expect, it } from "vitest";
import { buildDays, shade } from "@/lib/calendar";

describe("buildDays", () => {
  it("enumerates an inclusive UTC day range with counts and weekdays", () => {
    const days = buildDays("2026-07-06T00:00:00Z", "2026-07-08T12:00:00Z", {
      "2026-07-07": 9,
    });
    expect(days.map((d) => d.date)).toEqual(["2026-07-06", "2026-07-07", "2026-07-08"]);
    expect(days.find((d) => d.date === "2026-07-07")?.count).toBe(9);
    expect(days.find((d) => d.date === "2026-07-08")?.count).toBe(0);
    // 2026-07-06 is a Monday (UTC) → dow 1
    expect(days[0].dow).toBe(1);
  });
});

describe("shade", () => {
  it("returns the hairline token for empty days and scales ink with intensity", () => {
    expect(shade(0, 10)).toBe("var(--hairline)");
    expect(shade(10, 10)).toContain("90%"); // 25 + 65
    expect(shade(5, 10)).toContain("58%"); // 25 + round(0.5*65)
  });
});
