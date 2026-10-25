/** The bracket Nova's cursor draws around a target: a rectangle whose four corners are bitten out. */
export function framePath(w: number, h: number, c = 7): string {
  const r = Math.min(c, w / 2, h / 2);
  return [
    `M${r},0`,
    `H${w - r}`,
    `A${r},${r} 0 0 0 ${w},${r}`,
    `V${h - r}`,
    `A${r},${r} 0 0 0 ${w - r},${h}`,
    `H${r}`,
    `A${r},${r} 0 0 0 0,${h - r}`,
    `V${r}`,
    `A${r},${r} 0 0 0 ${r},0`,
    "Z",
  ].join(" ");
}
