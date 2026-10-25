import { AbsoluteFill, Easing, interpolate, interpolateColors, useCurrentFrame } from "remotion";

/**
 * Nova's opening shot. One day passes over one life in ten seconds, and the film loops without a seam:
 * every moving thing completes a whole number of cycles. Layers, back to front: sky, nebula, far stars,
 * orbit rings, the thread of moments, the sun and its anamorphic flare, the star at the centre, and
 * out-of-focus light in front of the lens. Grading (vignette, grain, halation) is done in ffmpeg.
 */
export const HERO = { width: 1920, height: 1080, fps: 30, frames: 300 } as const;

const TAU = Math.PI * 2;
const CX = 1210; // the subject sits right of centre, leaving the left of the frame for type
const CY = 540;
const DAY = [0, 0.25, 0.5, 0.75, 1];
const SKY_A = ["#5a2342", "#12525a", "#5b2f55", "#0b2a35", "#5a2342"];
const SKY_B = ["#26112a", "#0a2e34", "#25142c", "#041419", "#26112a"];
const SUN_COL = ["#ffb26b", "#ffe2a1", "#ff9a7a", "#cfe6ff", "#ffb26b"];

const rnd = (i: number, k: number) => Math.abs((Math.sin(i * 127.1 + k * 311.7) * 43758.5453) % 1);
const out = Easing.bezier(0.16, 1, 0.3, 1);

const STARS = Array.from({ length: 150 }, (_, i) => ({ x: rnd(i, 1) * 1920, y: rnd(i, 2) * 1080, r: 0.8 + rnd(i, 3) * 1.9, depth: rnd(i, 4), tw: 2 + Math.floor(rnd(i, 5) * 4), ph: rnd(i, 6) * TAU }));
const BOKEH = Array.from({ length: 16 }, (_, i) => ({ x: rnd(i, 7) * 2100 - 90, y: rnd(i, 8) * 1200 - 60, r: 34 + rnd(i, 9) * 110, blur: 8 + rnd(i, 10) * 20, a: 0.05 + rnd(i, 11) * 0.12, hue: [340, 38, 175, 320][i % 4], k: 1 + (i % 3), ph: rnd(i, 12) * TAU }));
const DUST = Array.from({ length: 70 }, (_, i) => ({ x: rnd(i, 13) * 1920, y: rnd(i, 14) * 1080, r: 1 + rnd(i, 15) * 2.4, k: 1 + (i % 3), ph: rnd(i, 16) * TAU, a: 0.2 + rnd(i, 17) * 0.6 }));
const NODES = [
  { a: 0.1, r: 318 }, { a: 0.85, r: 236 }, { a: 1.55, r: 330 }, { a: 2.3, r: 244 }, { a: 3.05, r: 322 },
  { a: 3.8, r: 238 }, { a: 4.55, r: 334 }, { a: 5.45, r: 246 },
].map((n) => ({ ...n, x: CX + n.r * Math.cos(n.a), y: CY + n.r * Math.sin(n.a) }));
const RINGS = [{ r: 190, laps: 3 }, { r: 400, laps: -2 }, { r: 560, laps: 1 }, { r: 780, laps: -1 }];

function smooth(points: { x: number; y: number }[]): string {
  const n = points.length;
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 0; i < n; i++) {
    const p0 = points[(i - 1 + n) % n], p1 = points[i], p2 = points[(i + 1) % n], p3 = points[(i + 2) % n];
    d += `C${p1.x + (p2.x - p0.x) / 6},${p1.y + (p2.y - p0.y) / 6} ${p2.x - (p3.x - p1.x) / 6},${p2.y - (p3.y - p1.y) / 6} ${p2.x},${p2.y}`;
  }
  return d + "Z";
}
const THREAD = smooth(NODES);
const angGap = (a: number, b: number) => {
  const d = (((a - b) % TAU) + TAU) % TAU;
  return d;
};

export const Hero = () => {
  const frame = useCurrentFrame();
  const t = frame / HERO.frames; // 0..1, loops
  const skyA = interpolateColors(t, DAY, SKY_A);
  const skyB = interpolateColors(t, DAY, SKY_B);
  const sunCol = interpolateColors(t, DAY, SUN_COL);

  // Camera: a slow breath, never a stop. Whole cycles only.
  const cam = {
    s: 1.045 + 0.02 * Math.sin(t * TAU),
    x: 14 * Math.sin(t * TAU * 2),
    y: 9 * Math.cos(t * TAU),
    r: 0.45 * Math.sin(t * TAU),
  };
  const par = (d: number) => ({ x: -cam.x * d * 3, y: -cam.y * d * 3 }); // depth through counter-motion

  const theta = Math.PI + t * TAU; // sun's angle on its orbit: dawn on the left, noon above, dusk right
  const R_SUN = 470;
  const sx = CX + R_SUN * Math.cos(theta);
  const sy = CY + R_SUN * Math.sin(theta);
  const breathe = 1 + 0.045 * Math.sin(t * TAU * 2);

  return (
    <AbsoluteFill style={{ background: "#02090c", overflow: "hidden" }}>
      {/* sky */}
      <AbsoluteFill style={{ background: `radial-gradient(115% 95% at 63% 48%, ${skyA} 0%, ${skyB} 48%, #02090c 100%)` }} />

      <AbsoluteFill style={{ transform: `translate(${cam.x}px, ${cam.y}px) rotate(${cam.r}deg) scale(${cam.s})`, transformOrigin: `${CX}px ${CY}px` }}>
        {/* nebula: ambient colour that drifts, so the dark is never flat */}
        {[0, 1, 2].map((i) => {
          const hue = ["rgba(255,120,170,0.34)", "rgba(40,190,180,0.26)", "rgba(255,170,90,0.2)"][i];
          const ox = [-260, 330, 60][i] + 70 * Math.sin(t * TAU + i * 2.1);
          const oy = [-170, 150, 260][i] + 50 * Math.cos(t * TAU + i);
          return <div key={i} style={{ position: "absolute", left: CX + ox - 560, top: CY + oy - 560, width: 1120, height: 1120, borderRadius: "50%", background: `radial-gradient(circle, ${hue}, transparent 62%)`, filter: "blur(36px)", mixBlendMode: "screen", opacity: 0.8 }} />;
        })}

        {/* far stars */}
        {STARS.map((s, i) => {
          const p = par(s.depth);
          const night = 0.35 + 0.65 * (0.5 - 0.5 * Math.cos(t * TAU * 2));
          return <div key={i} style={{ position: "absolute", left: s.x + p.x, top: s.y + p.y, width: s.r * 2, height: s.r * 2, borderRadius: "50%", background: "#fff6ec", opacity: night * (0.25 + 0.75 * (0.5 + 0.5 * Math.sin(t * TAU * s.tw + s.ph))) * (0.35 + s.depth * 0.5) }} />;
        })}

        <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
          <defs>
            <radialGradient id="bloom" cx="50%" cy="50%" r="50%">
              <stop offset="0" stopColor="#ff8faf" stopOpacity="0.85" />
              <stop offset="0.45" stopColor="#ff6fa0" stopOpacity="0.22" />
              <stop offset="1" stopColor="#ff6fa0" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="sunHalo" cx="50%" cy="50%" r="50%">
              <stop offset="0" stopColor={sunCol} stopOpacity="0.95" />
              <stop offset="0.18" stopColor={sunCol} stopOpacity="0.5" />
              <stop offset="1" stopColor={sunCol} stopOpacity="0" />
            </radialGradient>
            <linearGradient id="streak" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0" stopColor={sunCol} stopOpacity="0" />
              <stop offset="0.5" stopColor="#fff7e6" stopOpacity="1" />
              <stop offset="1" stopColor={sunCol} stopOpacity="0" />
            </linearGradient>
            <linearGradient id="starFill" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0" stopColor="#fff2f6" />
              <stop offset="0.55" stopColor="#ff8faf" />
              <stop offset="1" stopColor="#ff4f86" />
            </linearGradient>
            <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14" /></filter>
            <filter id="tight" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" /></filter>
          </defs>

          {/* orbit rings, each with a bright comet that travels it */}
          {RINGS.map((o, i) => {
            const len = TAU * o.r;
            const head = (t * o.laps * len) % len;
            return (
              <g key={o.r}>
                <circle cx={CX} cy={CY} r={o.r} fill="none" stroke="#f6dfe6" strokeOpacity={0.1 + 0.02 * i} strokeWidth={1.5} />
                <circle cx={CX} cy={CY} r={o.r} fill="none" stroke="#ffd7e3" strokeWidth={3} strokeLinecap="round" strokeDasharray={`${len * 0.12} ${len * 0.88}`} strokeDashoffset={-head} strokeOpacity={0.75} filter="url(#tight)" />
                <circle cx={CX} cy={CY} r={o.r} fill="none" stroke="#fff" strokeWidth={1.6} strokeLinecap="round" strokeDasharray={`${len * 0.12} ${len * 0.88}`} strokeDashoffset={-head} strokeOpacity={0.9} />
              </g>
            );
          })}

          {/* the thread of moments */}
          <path d={THREAD} fill="none" stroke="#ff8faf" strokeOpacity={0.22} strokeWidth={2.5} />
          <path d={THREAD} fill="none" stroke="#ffb3c8" strokeWidth={3.5} strokeLinecap="round" strokeDasharray="10 26" strokeDashoffset={-t * 36 * 28} strokeOpacity={0.85} />
          {NODES.map((n, i) => {
            const since = angGap(theta, n.a) / (TAU / 3); // 0 the instant the sun passes, fading to 1
            const lit = since < 1 ? Math.pow(1 - since, 2) : 0;
            const rip = since < 1 ? out(since) : 1;
            return (
              <g key={i}>
                {since < 1 && <circle cx={n.x} cy={n.y} r={16 + 120 * rip} fill="none" stroke="#ffe2a1" strokeWidth={2.5} strokeOpacity={0.6 * (1 - rip)} />}
                <circle cx={n.x} cy={n.y} r={30 + 60 * lit} fill={sunCol} opacity={0.38 * lit} filter="url(#soft)" />
                <circle cx={n.x} cy={n.y} r={11 + 8 * lit} fill="#ff8faf" />
                <circle cx={n.x} cy={n.y} r={4.5 + 4 * lit} fill="#fff4f7" />
              </g>
            );
          })}

          {/* the star at the centre: bloom, lens cross, then the star itself */}
          <circle cx={CX} cy={CY} r={300 * breathe} fill="url(#bloom)" />
          <rect x={CX - 700} y={CY - 1.5} width={1400} height={3} fill="url(#streak)" opacity={0.5 * breathe} filter="url(#tight)" />
          <rect x={CX - 1.5} y={CY - 380} width={3} height={760} fill="url(#streak)" opacity={0.28} transform={`rotate(90 ${CX} ${CY})`} filter="url(#tight)" />
          <g transform={`translate(${CX} ${CY}) rotate(${90 * t}) scale(${(210 / 24) * breathe}) translate(-12 -12)`}>
            <path d="M12 0C12.9 7.2 16.8 11.1 24 12 16.8 12.9 12.9 16.8 12 24 11.1 16.8 7.2 12.9 0 12 7.2 11.1 11.1 7.2 12 0Z" fill="url(#starFill)" />
          </g>
          <circle cx={CX} cy={CY} r={26} fill="#fff" opacity={0.85} filter="url(#tight)" />

          {/* the sun: shafts, halo, white-hot core, and an anamorphic streak that rides with it */}
          {Array.from({ length: 28 }, (_, k) => {
            const a = (TAU * k) / 28 + t * TAU * 0.5;
            const w = 0.012 + 0.008 * rnd(k, 3);
            const R = 1700;
            return <path key={k} d={`M${sx},${sy} L${sx + R * Math.cos(a - w)},${sy + R * Math.sin(a - w)} L${sx + R * Math.cos(a + w)},${sy + R * Math.sin(a + w)}Z`} fill={sunCol} opacity={0.07 + 0.05 * Math.sin(t * TAU * 3 + k)} filter="url(#tight)" />;
          })}
          <circle cx={sx} cy={sy} r={360} fill="url(#sunHalo)" opacity={0.7} />
          <rect x={sx - 900} y={sy - 6} width={1800} height={12} fill="url(#streak)" opacity={0.75} filter="url(#tight)" />
          <rect x={sx - 520} y={sy - 2} width={1040} height={4} fill="url(#streak)" opacity={0.9} />
          <circle cx={sx} cy={sy} r={46} fill={sunCol} />
          <circle cx={sx} cy={sy} r={26} fill="#fffaf0" />
        </svg>

        {/* out-of-focus light in front of the lens */}
        {BOKEH.map((b, i) => {
          const p = par(1.6);
          const x = b.x + p.x * b.k + 60 * Math.sin(t * TAU * b.k + b.ph);
          const y = b.y + p.y * b.k + 40 * Math.cos(t * TAU * b.k + b.ph);
          return <div key={i} style={{ position: "absolute", left: x - b.r, top: y - b.r, width: b.r * 2, height: b.r * 2, borderRadius: "50%", background: `radial-gradient(circle, hsla(${b.hue},90%,70%,${b.a * 1.4}) 0%, hsla(${b.hue},90%,65%,${b.a}) 62%, hsla(${b.hue},90%,60%,${b.a * 1.8}) 70%, transparent 74%)`, filter: `blur(${b.blur}px)`, mixBlendMode: "screen" }} />;
        })}
        {DUST.map((d, i) => {
          const p = par(1.1);
          const x = d.x + p.x + 90 * Math.sin(t * TAU * d.k + d.ph);
          const y = d.y + p.y + 60 * Math.cos(t * TAU * d.k + d.ph);
          return <div key={i} style={{ position: "absolute", left: x, top: y, width: d.r * 2, height: d.r * 2, borderRadius: "50%", background: "#ffe9c9", opacity: d.a * (0.5 + 0.5 * Math.sin(t * TAU * 3 + d.ph)) }} />;
        })}
      </AbsoluteFill>

      {/* a slow warm sweep across the lens as the sun passes the top of its arc */}
      <AbsoluteFill style={{ mixBlendMode: "screen", opacity: interpolate(Math.sin(t * TAU - Math.PI / 2 + 0.0), [0.6, 1], [0, 0.22], { extrapolateLeft: "clamp" }), background: "linear-gradient(105deg, transparent 20%, rgba(255,200,140,0.5) 45%, transparent 62%)", transform: `translateX(${interpolate(t, [0, 1], [-30, 30])}%)` }} />
    </AbsoluteFill>
  );
};
