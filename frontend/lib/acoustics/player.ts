/*
 * Nova acoustics — tiny synthesized room sounds, no audio files.
 * Everything is whisper-quiet (master gain ≤ 0.08) and only ever fires after a user gesture.
 * "Nothing sci-fi. More: Japanese camera shutter, mechanical keyboard, leather notebook."
 */

export type SoundName = "open" | "click" | "room-on" | "room-off";

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let room: { osc: OscillatorNode; gain: GainNode } | null = null;

function ensure(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.08; // whisper
    master.connect(ctx.destination);
  }
  return ctx;
}

/** Resume a suspended context (call from a user-gesture handler). */
export function resume(): void {
  const c = ensure();
  if (c && c.state === "suspended") void c.resume();
}

function tone(freq: number, start: number, dur: number, peak = 1): void {
  if (!ctx || !master) return;
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = "sine";
  osc.frequency.value = freq;
  g.gain.setValueAtTime(0.0001, start);
  g.gain.linearRampToValueAtTime(peak, start + 0.015);
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
  osc.connect(g);
  g.connect(master);
  osc.start(start);
  osc.stop(start + dur + 0.02);
}

function paperClick(): void {
  if (!ctx || !master) return;
  const dur = 0.035;
  const buf = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * dur), ctx.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < data.length; i++) {
    data[i] = (Math.random() * 2 - 1) * (1 - i / data.length); // decaying noise burst
  }
  const src = ctx.createBufferSource();
  src.buffer = buf;
  const bp = ctx.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.value = 2200;
  bp.Q.value = 0.8;
  const g = ctx.createGain();
  g.gain.value = 0.6;
  src.connect(bp);
  bp.connect(g);
  g.connect(master);
  src.start();
}

function roomOn(): void {
  if (!ctx || !master || room) return;
  const osc = ctx.createOscillator();
  osc.type = "sine";
  osc.frequency.value = 104;
  const g = ctx.createGain();
  g.gain.value = 0.0001;
  g.gain.linearRampToValueAtTime(0.22, ctx.currentTime + 0.6);
  osc.connect(g);
  g.connect(master);
  osc.start();
  room = { osc, gain: g };
}

function roomOff(): void {
  if (!ctx || !room) return;
  const { osc, gain } = room;
  gain.gain.linearRampToValueAtTime(0.0001, ctx.currentTime + 0.4);
  osc.stop(ctx.currentTime + 0.45);
  room = null;
}

export function play(name: SoundName): void {
  const c = ensure();
  if (!c) return;
  if (c.state === "suspended") void c.resume();
  const t = c.currentTime;
  switch (name) {
    case "open":
      tone(528, t, 0.5, 0.85);
      tone(792, t + 0.12, 0.6, 0.5);
      break;
    case "click":
      paperClick();
      break;
    case "room-on":
      roomOn();
      break;
    case "room-off":
      roomOff();
      break;
  }
}
