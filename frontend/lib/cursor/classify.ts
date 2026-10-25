/**
 * What is the pointer over, and so what should Nova's cursor be? A pure function of the element
 * under it, so every state can be tested without a browser.
 *
 *  press    a link, button, tab or choice: the cursor opens into a bracket around it
 *  blocked  the same, but unavailable: the dot dims and is struck through
 *  read     text you can read: the dot narrows to a line, like a caret
 *  field    somewhere you type: Nova's cursor steps aside for the real one
 *  film     the opening shot: the dot becomes light
 *  default  everywhere else: a knot trailing a thread
 */
export type CursorMode =
  | "default"
  | "press"
  | "blocked"
  | "read"
  | "field"
  | "film";
export type CursorTarget = {
  mode: CursorMode;
  el: Element | null;
  danger: boolean;
};

const FIELD =
  "input:not([type=range]):not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]), textarea, select, [contenteditable='true']";
const PRESS =
  "a[href], button, summary, [role='button'], [role='radio'], [role='tab'], [role='menuitem'], [data-cursor='press']";
const READ = "p, h1, h2, h3, h4, li, blockquote, figcaption, dt, dd, td";

export function classify(el: Element | null): CursorTarget {
  const none = { el: null, danger: false };
  if (!el) return { mode: "default", ...none };
  if (el.closest(FIELD)) return { mode: "field", ...none };
  const press = el.closest(PRESS);
  if (press) {
    const danger = Boolean(press.closest("[data-cursor-tone='danger']"));
    const off = press.matches("[disabled], [aria-disabled='true']");
    return { mode: off ? "blocked" : "press", el: press, danger };
  }
  if (el.closest("[data-cursor='film']")) return { mode: "film", ...none };
  if (el.closest(READ)) return { mode: "read", ...none };
  return { mode: "default", ...none };
}

/** A bracket only makes sense around something you could plausibly take in at a glance. */
export function worthFraming(rect: { width: number; height: number }): boolean {
  return (
    rect.width >= 16 &&
    rect.height >= 16 &&
    rect.width <= 560 &&
    rect.height <= 280
  );
}
