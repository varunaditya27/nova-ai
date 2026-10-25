import { describe, expect, it } from "vitest";
import { TypingTracker } from "./typingSignals";

describe("TypingTracker", () => {
  it("records a long draft cut down, with deletions and a start time", () => {
    const t = new TypingTracker();
    t.change("h", 1_000);
    t.change("hello there, I really need to tell you something", 5_000);
    t.change("hello there", 6_000);
    t.change("hi", 7_000);
    const s = t.snapshot("hi", 8_000);
    expect(s.deletion_occurred).toBe(true);
    expect(s.deletion_count).toBe(2);
    expect(s.peak_draft_length_chars).toBe(48);
    expect(s.final_draft_length_chars).toBe(2);
    expect(s.user_typing_started_at).toBe(new Date(1_000).toISOString());
    expect(s.is_burst).toBe(false);
  });

  it("flags rapid-fire messages as a burst and resets once the conversation pauses", () => {
    const t = new TypingTracker();
    t.change("one", 0);
    expect(t.snapshot("one", 1_000).is_burst).toBe(false);
    t.change("two", 2_000);
    const second = t.snapshot("two", 3_000);
    expect(second.is_burst).toBe(true);
    expect(second.burst_count).toBe(2);
    t.change("three", 60_000);
    const later = t.snapshot("three", 61_000);
    expect(later.is_burst).toBe(false);
    expect(later.burst_count).toBe(1);
  });
});
