import { describe, expect, it } from "vitest";
import { closeness, spectrums } from "./style";

describe("style copy", () => {
  it("turns learned preferences into plain sentences", () => {
    const s = spectrums({
      formality_preference: 0.2,
      response_length_preference: 0.9,
      question_tolerance: 0.5,
      unsolicited_advice_tolerance: 0.1,
    });
    expect(s[0].sentence).toContain("casually");
    expect(s[1].sentence).toContain("depth");
    expect(s[2].sentence).toContain("moderate");
    expect(s[3].sentence).toContain("hold back advice");
  });
  it("clamps wild values onto the track", () => {
    expect(
      spectrums({
        formality_preference: 5,
        response_length_preference: -2,
        question_tolerance: 0.5,
        unsolicited_advice_tolerance: 0.5,
      })[0].at,
    ).toBe(1);
  });
  it("describes closeness in words", () => {
    expect(closeness(0.1)).toBe("Still early");
    expect(closeness(0.9)).toBe("Very close");
  });
});
