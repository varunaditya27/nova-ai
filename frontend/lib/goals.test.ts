import { describe, expect, it } from "vitest";
import { habitCadence, statusWords, streakWords } from "./goals";

describe("goals copy", () => {
  it("never shows a raw status key", () => {
    expect(statusWords("at_risk")).toContain("Slipping");
    expect(statusWords("on_track")).toBe("On track");
    expect(statusWords("some_new_state")).toBe("some new state");
  });
  it("counts streaks in the habit's own unit", () => {
    expect(streakWords(0, "daily")).toContain("tell Nova");
    expect(streakWords(1, "daily")).toBe("1 day in a row");
    expect(streakWords(3, "weekly")).toBe("3 weeks in a row");
    expect(habitCadence("weekdays")).toBe("on weekdays");
  });
});
