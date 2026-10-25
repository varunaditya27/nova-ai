import { describe, expect, it } from "vitest";
import { EVENT_TYPES, feeling, howOften, plainEvent, relationshipLabel } from "./people";

describe("people copy", () => {
  it("describes a relationship in words with its direction", () => {
    expect(feeling({ relationship_valence: 0.6, valence_trend: 0 })).toBe("Things sound warm between you.");
    expect(feeling({ relationship_valence: -0.6, valence_trend: -0.3 })).toContain("getting harder");
    expect(feeling({ relationship_valence: 0, valence_trend: 0.3 })).toContain("getting better");
  });

  it("never shows an enum code as a label", () => {
    expect(relationshipLabel("family_immediate")).toBe("Close family");
    expect(relationshipLabel("peer_academic")).toBe("Classmate");
    expect(relationshipLabel("brand_new_kind")).toBe("Brand new kind");
    for (const label of EVENT_TYPES.map(plainEvent)) expect(label).not.toMatch(/_/);
    expect(plainEvent("conflict_resolution")).toBe("An argument was settled");
  });

  it("says nothing when frequency is unknown, rather than a placeholder", () => {
    expect(howOften("unknown")).toBe("");
    expect(howOften("daily")).toContain("every day");
    expect(howOften("something_else")).toBe("");
  });
});
