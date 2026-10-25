import { describe, expect, it } from "vitest";
import { EMPTY, NOTES, daySeed, hello, partOf, pick } from "./voice";
import { leanDegrees } from "./companion/lean";

const at = (h: number) => new Date(2026, 9, 25, h, 0, 0);

describe("voice", () => {
  it("greets by the hour, and asks rather than states when it is very late", () => {
    expect(hello(at(9), "Asha").headline).toBe("Good morning, Asha.");
    expect(hello(at(14)).headline).toBe("Good afternoon.");
    expect(hello(at(19), "Asha").headline).toBe("Good evening, Asha.");
    expect(hello(at(2), "Asha").headline).toBe("Still up, Asha?");
  });

  it("covers every hour of the day", () => {
    for (let h = 0; h < 24; h++) expect(partOf(at(h))).toBeTruthy();
  });

  it("picks the same aside all day and a different one tomorrow", () => {
    expect(hello(at(9)).aside).toBe(hello(at(11)).aside);
    const next = new Date(2026, 9, 26, 9);
    expect(daySeed(next)).toBe(daySeed(at(9)) + 1);
  });

  it("picks deterministically and wraps around", () => {
    expect(pick(["a", "b", "c"], 4)).toBe("b");
    expect(pick(["a", "b", "c"], -1)).toBe("b");
  });

  it("never leaves a page without its aside or an empty state without its note", () => {
    for (const note of Object.values(NOTES)) expect(note.length).toBeGreaterThan(3);
    for (const e of Object.values(EMPTY)) {
      expect(e.title && e.body && e.note).toBeTruthy();
      expect(e.body).not.toMatch(/\d{4}-\d{2}-\d{2}/); // no raw timestamps
    }
  });
});

describe("leanDegrees", () => {
  const at0 = { x: 100, y: 100 };
  it("turns toward the pointer, not past a gentle limit", () => {
    expect(leanDegrees(at0, { x: 400, y: 100 })).toBeGreaterThan(0);
    expect(leanDegrees(at0, { x: -200, y: 100 })).toBeLessThan(0);
    expect(Math.abs(leanDegrees(at0, { x: 140, y: 100 }))).toBeLessThanOrEqual(9);
  });
  it("stays upright with the pointer straight above, and when it is on top of it", () => {
    expect(leanDegrees(at0, { x: 100, y: 0 })).toBeCloseTo(0);
    expect(leanDegrees(at0, at0)).toBe(0);
  });
  it("leans less the further away the pointer is", () => {
    expect(leanDegrees(at0, { x: 200, y: 100 })).toBeGreaterThan(
      leanDegrees(at0, { x: 1000, y: 100 }),
    );
  });
});
