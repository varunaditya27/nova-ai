/** One step of a critically damped spring: it arrives smoothly and never overshoots. */
export function dampStep(
  pos: number,
  vel: number,
  target: number,
  omega: number,
  dt: number,
): [number, number] {
  const x = pos - target;
  const e = Math.exp(-omega * dt);
  const k = (vel + omega * x) * dt;
  return [target + (x + k) * e, (vel - omega * k) * e];
}

/** How many recent positions the thread keeps: none when still, longer the faster you move. */
export function trailLength(speed: number, max = 28): number {
  return Math.round(Math.min(max, speed / 40));
}

/** Angle (degrees) a body leans into its direction of travel, within limits. */
export function lean(vx: number, limit = 28): number {
  return Math.max(-limit, Math.min(limit, vx * 0.03));
}
