import { describe, expect, it } from "vitest";
import { classify, worthFraming } from "./classify";
import { framePath } from "./frame";
import { dampStep, lean, trailLength } from "./physics";

const el = (html: string) => {
  document.body.innerHTML = html;
  return document.body.querySelector("[data-t]")!;
};

describe("classify", () => {
  it("steps aside over anywhere you type", () => {
    expect(classify(el("<textarea data-t></textarea>")).mode).toBe("field");
    expect(classify(el('<input data-t type="text">')).mode).toBe("field");
  });
  it("brackets buttons and links, and finds the button from a child", () => {
    const t = classify(el("<button><span data-t>Go</span></button>"));
    expect(t.mode).toBe("press");
    expect(t.el?.tagName).toBe("BUTTON");
    expect(classify(el('<a href="/x" data-t>x</a>')).mode).toBe("press");
    expect(classify(el('<div role="tab" data-t></div>')).mode).toBe("press");
  });
  it("marks unavailable things as blocked", () => {
    expect(classify(el("<button disabled data-t>x</button>")).mode).toBe(
      "blocked",
    );
    expect(
      classify(el('<div role="button" aria-disabled="true" data-t></div>'))
        .mode,
    ).toBe("blocked");
  });
  it("flags destructive actions", () => {
    expect(
      classify(
        el(
          '<div data-cursor-tone="danger"><button data-t>Forget</button></div>',
        ),
      ).danger,
    ).toBe(true);
    expect(classify(el("<button data-t>Keep</button>")).danger).toBe(false);
  });
  it("narrows to a line over reading text, but a link inside text is still a link", () => {
    expect(classify(el("<p><span data-t>words</span></p>")).mode).toBe("read");
    expect(classify(el('<p><a href="/x" data-t>words</a></p>')).mode).toBe(
      "press",
    );
  });
  it("becomes light over the film", () => {
    expect(
      classify(el('<section data-cursor="film"><div data-t></div></section>'))
        .mode,
    ).toBe("film");
  });
  it("is the plain knot everywhere else, and when there is no target", () => {
    expect(classify(el("<div data-t></div>")).mode).toBe("default");
    expect(classify(null).mode).toBe("default");
  });
});

describe("worthFraming", () => {
  it("frames things you can take in at a glance, not whole panels or specks", () => {
    expect(worthFraming({ width: 120, height: 48 })).toBe(true);
    expect(worthFraming({ width: 900, height: 600 })).toBe(false);
    expect(worthFraming({ width: 8, height: 8 })).toBe(false);
  });
});

describe("framePath", () => {
  it("draws a closed outline with four concave bites", () => {
    const d = framePath(100, 40, 7);
    expect(d.startsWith("M7,0")).toBe(true);
    expect(d.match(/A7,7 0 0 0/g)).toHaveLength(4);
    expect(d.endsWith("Z")).toBe(true);
  });
  it("shrinks the bite to fit a tiny target", () => {
    expect(framePath(10, 10, 7)).toContain("A5,5");
  });
});

describe("physics", () => {
  it("arrives at the target without overshooting", () => {
    let [p, v] = [0, 0];
    let max = 0;
    for (let i = 0; i < 240; i++) {
      [p, v] = dampStep(p, v, 100, 14, 1 / 60);
      max = Math.max(max, p);
    }
    expect(max).toBeLessThanOrEqual(100.0001);
    expect(p).toBeGreaterThan(99.99);
  });
  it("keeps no thread when still and a longer one when fast", () => {
    expect(trailLength(0)).toBe(0);
    expect(trailLength(2000)).toBeGreaterThan(trailLength(400));
    expect(trailLength(1e6)).toBe(28);
  });
  it("leans into travel, within limits", () => {
    expect(lean(500)).toBeGreaterThan(0);
    expect(lean(-500)).toBeLessThan(0);
    expect(Math.abs(lean(1e5))).toBe(28);
  });
});
