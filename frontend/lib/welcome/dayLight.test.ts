import { describe, expect, it } from "vitest";
import { dayLight, heroHour } from "./dayLight";

describe("dayLight", () => {
  it("moves left to right across the page through the day, staying off the edges", () => {
    const hours = [5, 8, 12, 17, 20];
    const at = hours.map((h) => dayLight(h).at);
    expect(at).toEqual([...at].sort((a, b) => a - b));
    expect(at[0]).toBeGreaterThan(0);
    expect(at[at.length - 1]).toBeLessThan(1);
  });

  it("holds at the edges before first light and after last light", () => {
    expect(dayLight(2).at).toBe(dayLight(5).at);
    expect(dayLight(23).at).toBe(dayLight(20).at);
  });

  it("is brightest at midday, dim at night, and leans one way in the morning and the other in the evening", () => {
    expect(dayLight(12.5).strength).toBeGreaterThan(dayLight(6).strength);
    expect(dayLight(23).strength).toBeLessThan(dayLight(12.5).strength);
    expect(dayLight(6).skew).toBeGreaterThan(0);
    expect(dayLight(19).skew).toBeLessThan(0);
  });

  it("changes colour between dawn, day, dusk and night", () => {
    const tints = [6, 12, 18, 23].map((h) => dayLight(h).tint);
    expect(new Set(tints).size).toBe(4);
  });
});

describe("heroHour", () => {
  it("is the real hour when the room's light matches the clock", () => {
    expect(heroHour("day", 14.25)).toBe(14.25);
  });

  it("stands in for the hour when the room was set to another light", () => {
    expect(heroHour("night", 14.25)).toBe(23);
    expect(heroHour("day", 22)).toBe(12.5);
  });
});
