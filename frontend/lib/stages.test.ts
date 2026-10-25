import { describe, expect, it } from "vitest";
import { stageById, toNextStage } from "./stages";

describe("stages", () => {
  it("falls back to the first stage for an unknown id", () => {
    expect(stageById("nonsense").id).toBe("new");
  });
  it("says how many conversations remain until the next stage", () => {
    const n = toNextStage("new", 2);
    expect(n?.next.id).toBe("acquaintance");
    expect(n?.remaining).toBe(2); // sessions 3 is still "new"; the 4th moves on
  });
  it("has no next stage at the last", () => {
    expect(toNextStage("close", 300)).toBeNull();
  });
});
