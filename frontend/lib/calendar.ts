export type CalendarDay = { date: string; count: number; dow: number };

/** Iterate a date range in UTC so day keys line up with the backend's date strings. */
export function buildDays(
  start: string,
  end: string,
  counts: Record<string, number>
): CalendarDay[] {
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

/** A warm activity shade — ink intensity scaled by count; hairline for empty days. */
export function shade(count: number, max: number): string {
  if (count <= 0) return "var(--hairline)";
  const ratio = Math.min(1, count / max);
  return `color-mix(in srgb, var(--ink) ${Math.round(25 + ratio * 65)}%, var(--surface))`;
}
