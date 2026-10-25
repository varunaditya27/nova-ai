/** Human-relative time ("yesterday", "3 days ago") — the UI never shows raw ISO to the user. */
export function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = then - Date.now();
  const abs = Math.abs(diff);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000_000],
    ["month", 2_592_000_000],
    ["week", 604_800_000],
    ["day", 86_400_000],
    ["hour", 3_600_000],
    ["minute", 60_000],
  ];
  for (const [unit, ms] of units) {
    if (abs >= ms || unit === "minute")
      return rtf.format(Math.round(diff / ms), unit);
  }
  return "just now";
}

const WEEKDAY = new Intl.DateTimeFormat("en", { weekday: "long" });
const LONG_DATE = new Intl.DateTimeFormat("en", {
  day: "numeric",
  month: "long",
});
const LONG_DATE_YEAR = new Intl.DateTimeFormat("en", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

export function partOfDay(
  date: Date,
): "morning" | "afternoon" | "evening" | "night" {
  const h = date.getHours();
  if (h >= 5 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 22) return "evening";
  return "night";
}

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/** Whole calendar days from `from` to `to` (negative when `to` is earlier). */
export function dayDiff(to: Date, from: Date = new Date()): number {
  return Math.round((startOfDay(to) - startOfDay(from)) / 86_400_000);
}

/** "Today evening", "Yesterday morning", "Tuesday night", "12 October" — how people say it. */
export function humanDay(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const diff = dayDiff(d, now);
  const part = partOfDay(d);
  if (diff === 0) return `This ${part}`;
  if (diff === -1) return `Yesterday ${part}`;
  if (diff > -7 && diff < 0) return `${WEEKDAY.format(d)} ${part}`;
  const sameYear = d.getFullYear() === now.getFullYear();
  return (sameYear ? LONG_DATE : LONG_DATE_YEAR).format(d);
}

export function longDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : LONG_DATE_YEAR.format(d);
}

/** "38 days to go", "Tomorrow", "Today", "3 days overdue". */
export function countdown(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const diff = dayDiff(d, now);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff > 1) return `${diff} days to go`;
  return `${Math.abs(diff)} day${Math.abs(diff) === 1 ? "" : "s"} overdue`;
}

/** "Good morning" — from the browser's own clock, so it is right wherever the person actually is. */
export function greetingFor(date: Date): string {
  const h = date.getHours();
  if (h >= 5 && h < 12) return "Good morning";
  if (h >= 12 && h < 17) return "Good afternoon";
  if (h >= 17 && h < 22) return "Good evening";
  return "Still up";
}

const DAY_MONTH = new Intl.DateTimeFormat("en", {
  day: "numeric",
  month: "long",
});
const DAY_MONTH_SHORT = new Intl.DateTimeFormat("en", {
  day: "numeric",
  month: "short",
});

/** "12–18 October" when within one month, "29 Sep – 5 Oct" across two. */
export function weekRange(start: string | null, end: string | null): string {
  if (!start) return "";
  const s = new Date(start);
  const e = end ? new Date(end) : s;
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return "";
  if (s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear()) {
    return `${s.getDate()}–${DAY_MONTH.format(e)}`;
  }
  return `${DAY_MONTH_SHORT.format(s)} – ${DAY_MONTH_SHORT.format(e)}`;
}
