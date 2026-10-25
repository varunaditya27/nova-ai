export type Point = { x: number; y: number };

/** Draw the thread the dot pulls behind it: thick and bright at the knot, thinning to nothing at the tail. */
export function drawTrail(
  ctx: CanvasRenderingContext2D,
  points: Point[],
  color: string,
  width: number,
): void {
  const n = points.length;
  ctx.lineCap = "round";
  ctx.strokeStyle = color;
  for (let i = 1; i < n; i++) {
    const t = i / n;
    ctx.globalAlpha = t * t * 0.85;
    ctx.lineWidth = Math.max(0.6, width * t);
    ctx.beginPath();
    ctx.moveTo(points[i - 1].x, points[i - 1].y);
    ctx.lineTo(points[i].x, points[i].y);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
}
