import { describe, expect, it } from "vitest";
import { mergeProactiveItems } from "./merge";
import type { ProactiveItem, ProactiveStreamItem } from "@/lib/api/types";

function polled(overrides: Partial<ProactiveItem> = {}): ProactiveItem {
  return {
    item_id: "p1",
    item_type: "goal_check_in",
    status: "pending",
    content_basis: "internal fragment",
    message: "a real message",
    current_priority: 0.5,
    ...overrides,
  };
}

function streamed(overrides: Partial<ProactiveStreamItem> = {}): ProactiveStreamItem {
  return { item_id: "p1", item_type: "goal_check_in", message: "a real message",
          current_priority: 0.5, ...overrides };
}

describe("mergeProactiveItems", () => {
  it("drops polled items with no generated message yet", () => {
    const out = mergeProactiveItems([polled({ message: "" })], []);
    expect(out).toEqual([]);
  });

  it("includes polled items that already have a message", () => {
    const out = mergeProactiveItems([polled()], []);
    expect(out).toHaveLength(1);
    expect(out[0].message).toBe("a real message");
  });

  it("dedupes by item_id, preferring the streamed version on overlap", () => {
    const out = mergeProactiveItems(
      [polled({ item_id: "p1", message: "polled text" })],
      [streamed({ item_id: "p1", message: "streamed text" })]
    );
    expect(out).toHaveLength(1);
    expect(out[0].message).toBe("streamed text");
  });

  it("sorts by current_priority, highest first", () => {
    const out = mergeProactiveItems(
      [polled({ item_id: "low", current_priority: 0.2 }),
       polled({ item_id: "high", current_priority: 0.9 })],
      []
    );
    expect(out.map((i) => i.item_id)).toEqual(["high", "low"]);
  });

  it("merges disjoint polled and streamed items", () => {
    const out = mergeProactiveItems(
      [polled({ item_id: "a" })],
      [streamed({ item_id: "b" })]
    );
    expect(out.map((i) => i.item_id).sort()).toEqual(["a", "b"]);
  });
});
