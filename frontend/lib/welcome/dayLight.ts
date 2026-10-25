import { lightForHour, type Light } from "@/components/ThemeProvider";

/** The hours a window's light crosses the page: first light to last. */
const FIRST = 5;
const LAST = 20;
/** Keeps the light, and the ruler's end ticks, off the very edge of the page. */
const EDGE = 0.03;

const TINT: Record<Light, string> = {
  dawn: "#ffb08a",
  day: "#fff0cf",
  dusk: "#ff9a5c",
  night: "#9db8ff",
};
const STAND_IN_HOUR: Record<Light, number> = { dawn: 6.5, day: 12.5, dusk: 18.5, night: 23 };

export type DayLight = {
  /** Where the light lands, as a share of the page width, left (first light) to right (last light). */
  at: number;
  /** Lean of the window's shadow in degrees: long and slanted at the ends of the day, upright at noon. */
  skew: number;
  /** How bright the light is, 0 to 1. */
  strength: number;
  tint: string;
};

export function dayLight(hour: number): DayLight {
  const p = Math.min(1, Math.max(0, (hour - FIRST) / (LAST - FIRST)));
  const light = lightForHour(hour);
  return {
    at: EDGE + (1 - 2 * EDGE) * p,
    skew: 34 - 68 * p,
    strength: light === "night" ? 0.35 : 0.3 + 0.5 * Math.sin(Math.PI * p),
    tint: TINT[light],
  };
}

/** The hour to draw: the real one, unless the room was set to another light than the clock gives ("Room light: Always dark"). */
export function heroHour(shown: Light, hour: number): number {
  return lightForHour(hour) === shown ? hour : STAND_IN_HOUR[shown];
}
