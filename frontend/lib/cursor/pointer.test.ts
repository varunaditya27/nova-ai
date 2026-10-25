import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(path.resolve(__dirname, "../../app/pointer.css"), "utf8");
const pointers = [...css.matchAll(/--pointer-(\w+): url\("data:image\/svg\+xml,([^"]+)"\)( [\d ]+);/g)];

/** A browser drops a bad cursor image without a word, so every way it can go wrong is checked here. */
describe("pointer.css", () => {
  it("defines the four states for day and for night", () => {
    const names = pointers.map((m) => m[1]);
    for (const state of ["rest", "press", "blocked", "busy"]) {
      expect(names.filter((n) => n === state)).toHaveLength(2);
    }
  });

  it.each(pointers.map((m) => [m[1], m[2], m[3]]))("%s is a valid 32px cursor image", (_, svg, hotspot) => {
    const decoded = decodeURIComponent(svg);
    expect(decoded).toMatch(/^<svg [^>]*width='32' height='32'/);
    expect(svg).not.toContain("#");
    expect(hotspot).toBe(" 3 3");
  });

  it("gives every cursor declaration a keyword fallback", () => {
    const declarations = [...css.matchAll(/cursor: ([^;]+);/g)].map((m) => m[1]);
    expect(declarations.length).toBeGreaterThan(0);
    for (const d of declarations) {
      expect(d).toMatch(/^(var\(--pointer-\w+\), )?(auto|pointer|not-allowed|progress|text)$/);
    }
  });
});
