export type CalendarDay = { date: string; count: number; dow: number };

/** Iterate a date range in UTC so day keys line up with the backend's date strings. */
export function buildDays(start: string, end: string, counts: Record<string, number>): CalendarDay[] {
  const days: CalendarDay[] = [];
  const s = new Date(start);
  const e = new Date(end);
  let cur = Date.UTC(s.getUTCFullYear(), s.getUTCMonth(), s.getUTCDate());
  const last = Date.UTC(e.getUTCFullYear(), e.getUTCMonth(), e.getUTCDate());
  let guard = 0;
  while (cur <= last && guard++ < 400) {
    const dt = new Date(cur);
    const key = dt.toISOString().slice(0, 10);
    days.push({ date: key, count: counts[key] ?? 0, dow: dt.getUTCDay() });
    cur += 86_400_000;
  }
  return days;
}

/** First and last instant of a UTC month, as ISO strings the backend understands. */
export function monthRange(year: number, month: number): { start: string; end: string } {
  return {
    start: new Date(Date.UTC(year, month, 1)).toISOString(),
    end: new Date(Date.UTC(year, month + 1, 0, 23, 59, 59)).toISOString(),
  };
}

/** Columns to skip before day 1 in a Monday-first week grid. */
export function mondayOffset(dow: number): number {
  return (dow + 6) % 7;
}

/**
 * A day's tone on the quilt: an empty day is the sunk tone; busier days deepen toward the accent.
 * The text colour flips once the fill is dark enough to need it.
 */
export function quiltTone(count: number, max: number): { background: string; color: string } {
  if (count <= 0 || max <= 0) return { background: "var(--sunk)", color: "var(--mute)" };
  const ratio = Math.min(1, count / max);
  const pct = Math.round(22 + ratio * 78);
  return {
    background: `color-mix(in srgb, var(--accent) ${pct}%, var(--sunk))`,
    color: pct >= 58 ? "var(--accent-ink)" : "var(--ink)",
  };
}
