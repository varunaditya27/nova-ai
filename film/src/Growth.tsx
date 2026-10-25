import { AbsoluteFill, Easing, interpolate, interpolateColors, useCurrentFrame } from "remotion";

/**
 * A mind, growing. Scrubbed by scroll rather than played: frame 0 is a single star on the first day,
 * the last frame is a dense web two years on. Moments appear one by one and join the thread, the camera
 * pulls back as the web grows, a day passes once across the whole film, and the weeks of a year tick
 * into a ring around it.
 */
export const GROWTH = { width: 1000, height: 1000, fps: 30, frames: 120 } as const;

const TAU = Math.PI * 2;
const C = 500;
const N = 26;
const KEYS = [0, 0.33, 0.66, 1];
const SKY_A = ["#4a1d3c", "#14585e", "#4b2650", "#0a2230"];
const SKY_B = ["#1d0f26", "#082e33", "#1c1230", "#03111a"];
const SUN = ["#ffb347", "#ffe2a1", "#ff9a7a", "#cfe6ff"];
const clamp = (v: number) => Math.max(0, Math.min(1, v));
const out = Easing.bezier(0.16, 1, 0.3, 1);
const rnd = (i: number, k: number) => Math.abs((Math.sin(i * 127.1 + k * 311.7) * 43758.5453) % 1);

const NODES = Array.from({ length: N }, (_, i) => {
  const a = i * 2.39996 + 0.4;
  const r = 78 + 330 * Math.sqrt((i + 1) / N);
  return { x: C + r * Math.cos(a), y: C + r * Math.sin(a), at: 0.04 + 0.84 * Math.pow(i / (N - 1), 0.9) };
});
const EDGES = NODES.map((n, i) => {
  if (i === 0) return null;
  let best = 0;
  let bd = Infinity;
  for (let j = 0; j < i; j++) {
    const d = Math.hypot(n.x - NODES[j].x, n.y - NODES[j].y);
    if (d < bd) { bd = d; best = j; }
  }
  return best;
});
const STARS = Array.from({ length: 90 }, (_, i) => ({ x: rnd(i, 1) * 1000, y: rnd(i, 2) * 1000, r: 0.8 + rnd(i, 3) * 1.8, ph: rnd(i, 4) * TAU }));

export const Growth = () => {
  const f = useCurrentFrame();
  const p = f / (GROWTH.frames - 1);
  const cam = interpolate(Easing.inOut(Easing.cubic)(p), [0, 1], [2.3, 1]);
  const rot = interpolate(p, [0, 1], [0, 22]);
  const skyA = interpolateColors(p, KEYS, SKY_A);
  const skyB = interpolateColors(p, KEYS, SKY_B);
  const sun = interpolateColors(p, KEYS, SUN);
  const night = clamp((p - 0.55) / 0.3);
  const theta = Math.PI + p * TAU * 0.92;
  const sx = C + 430 * Math.cos(theta);
  const sy = C + 430 * Math.sin(theta);
  const weeks = Math.floor(26 * clamp((p - 0.42) / 0.22));
  const weeks2 = Math.floor(52 * clamp((p - 0.74) / 0.22));

  return (
    <AbsoluteFill style={{ background: `radial-gradient(100% 100% at 50% 50%, ${skyA} 0%, ${skyB} 62%, #02090c 100%)`, overflow: "hidden" }}>
      <svg viewBox="0 0 1000 1000" width="100%" height="100%" style={{ transform: `scale(${cam}) rotate(${rot}deg)`, transformOrigin: "50% 50%" }}>
        <defs>
          <radialGradient id="g-bloom"><stop offset="0" stopColor="#ff8faf" stopOpacity="0.9" /><stop offset="0.5" stopColor="#ff6fa0" stopOpacity="0.2" /><stop offset="1" stopColor="#ff6fa0" stopOpacity="0" /></radialGradient>
          <radialGradient id="g-sun"><stop offset="0" stopColor={sun} stopOpacity="0.9" /><stop offset="0.25" stopColor={sun} stopOpacity="0.35" /><stop offset="1" stopColor={sun} stopOpacity="0" /></radialGradient>
          <filter id="g-soft" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="9" /></filter>
        </defs>

        {STARS.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="#fff6ec" opacity={night * (0.3 + 0.7 * (0.5 + 0.5 * Math.sin(p * TAU * 3 + s.ph)))} />
        ))}

        <circle cx={C} cy={C} r={430} fill="none" stroke="#f6dfe6" strokeOpacity="0.1" strokeWidth="1.5" />
        <circle cx={C} cy={C} r={200} fill="none" stroke="#f6dfe6" strokeOpacity="0.07" strokeWidth="1.5" />

        {Array.from({ length: 26 }, (_, k) => {
          const a = (TAU * k) / 26 - Math.PI / 2;
          const on = k < weeks;
          return <line key={k} x1={C + 452 * Math.cos(a)} y1={C + 452 * Math.sin(a)} x2={C + 470 * Math.cos(a)} y2={C + 470 * Math.sin(a)} stroke={on ? "#ffd7a1" : "#f6dfe6"} strokeOpacity={on ? 0.95 : 0.12} strokeWidth={on ? 3 : 2} strokeLinecap="round" />;
        })}
        {Array.from({ length: 52 }, (_, k) => {
          const a = (TAU * k) / 52 - Math.PI / 2;
          const on = k < weeks2;
          return <line key={k} x1={C + 478 * Math.cos(a)} y1={C + 478 * Math.sin(a)} x2={C + 490 * Math.cos(a)} y2={C + 490 * Math.sin(a)} stroke={on ? "#ff8faf" : "#f6dfe6"} strokeOpacity={on ? 0.9 : 0.08} strokeWidth={on ? 2.5 : 1.5} strokeLinecap="round" />;
        })}

        {NODES.map((n, i) => {
          const from = EDGES[i];
          if (from === null) return null;
          const q = out(clamp((p - n.at) / 0.06));
          const a = NODES[from];
          return <line key={i} x1={a.x} y1={a.y} x2={a.x + (n.x - a.x) * q} y2={a.y + (n.y - a.y) * q} stroke="#ffb3c8" strokeOpacity={0.55} strokeWidth={2} strokeLinecap="round" />;
        })}

        <circle cx={sx} cy={sy} r={220} fill="url(#g-sun)" />
        <circle cx={sx} cy={sy} r={30} fill={sun} />

        {NODES.map((n, i) => {
          const q = clamp((p - n.at) / 0.045);
          if (q <= 0) return null;
          const e = out(q);
          const d = Math.abs(((theta - Math.atan2(n.y - C, n.x - C)) % TAU + TAU) % TAU);
          const lit = Math.max(0, 1 - Math.min(d, TAU - d) / 0.9) ** 2;
          return (
            <g key={i}>
              <circle cx={n.x} cy={n.y} r={10 + 90 * e} fill="none" stroke="#ffe2a1" strokeWidth={2} strokeOpacity={0.7 * (1 - e)} />
              <circle cx={n.x} cy={n.y} r={26 + 34 * lit} fill={sun} opacity={0.35 * lit} filter="url(#g-soft)" />
              <circle cx={n.x} cy={n.y} r={(9 + 5 * lit) * e} fill="#ff8faf" />
              <circle cx={n.x} cy={n.y} r={(3.6 + 3 * lit) * e} fill="#fff4f7" />
            </g>
          );
        })}

        <circle cx={C} cy={C} r={170 * (1 + 0.04 * Math.sin(p * TAU * 4))} fill="url(#g-bloom)" />
        <g transform={`translate(${C} ${C}) rotate(${90 * p}) scale(${120 / 24}) translate(-12 -12)`}>
          <path fill="#ffd0de" d="M12 0C12.9 7.2 16.8 11.1 24 12 16.8 12.9 12.9 16.8 12 24 11.1 16.8 7.2 12.9 0 12 7.2 11.1 11.1 7.2 12 0Z" />
        </g>
        <circle cx={C} cy={C} r={18} fill="#fff" opacity={0.85} filter="url(#g-soft)" />
      </svg>
    </AbsoluteFill>
  );
};
