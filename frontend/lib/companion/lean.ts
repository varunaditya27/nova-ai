/** How far (in degrees) a character turns toward a point: a gentle lean, never a spin, fading with distance. */
export function leanDegrees(
  from: { x: number; y: number },
  to: { x: number; y: number },
  max = 9,
): number {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.hypot(dx, dy);
  if (dist < 1) return 0;
  const reach = 1 - Math.min(dist, 900) / 1800; // 1 up close, 0.5 far away
  return Math.max(-max, Math.min(max, (dx / dist) * max * reach));
}
