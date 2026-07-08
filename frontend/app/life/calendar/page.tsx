"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { LifeNav } from "@/components/life/LifeNav";
import { useCalendar } from "@/lib/hooks/useLife";

type Day = { date: string; count: number; dow: number };

/** Iterate the range in UTC so day keys line up with the backend's date strings. */
function buildDays(start: string, end: string, counts: Record<string, number>): Day[] {
  const days: Day[] = [];
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

function shade(count: number, max: number): string {
  if (count <= 0) return "var(--hairline)";
  const ratio = Math.min(1, count / max);
  return `color-mix(in srgb, var(--ink) ${Math.round(25 + ratio * 65)}%, var(--surface))`;
}

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

/** The Calendar — a warm activity heatmap. */
export default function Calendar() {
  const { data, isLoading } = useCalendar();
  const days = data ? buildDays(data.start, data.end, data.days) : [];
  const max = Math.max(1, ...days.map((d) => d.count));
  const lead = days.length ? days[0].dow : 0;

  return (
    <PageShell title="The calendar" description="Every day you and Nova spent together.">
      <LifeNav />
      {isLoading && <div className="h-40 max-w-xs rounded-md bg-hairline/30" />}
      {data && (
        <div>
          <div className="grid max-w-[320px] grid-cols-7 gap-1.5">
            {WEEKDAYS.map((w, i) => (
              <span key={i} className="text-center font-mono text-[10px] text-ink-faint">
                {w}
              </span>
            ))}
            {Array.from({ length: lead }).map((_, i) => (
              <span key={`pad-${i}`} />
            ))}
            {days.map((d) => (
              <span
                key={d.date}
                title={`${d.date}: ${d.count} message${d.count === 1 ? "" : "s"}`}
                className="aspect-square rounded-[3px] border border-hairline/50"
                style={{ background: shade(d.count, max) }}
              />
            ))}
          </div>
          <div className="mt-5 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
            <span className="mr-1">less</span>
            {[0, max * 0.25, max * 0.5, max].map((c, i) => (
              <span
                key={i}
                className="h-3 w-3 rounded-[3px] border border-hairline/50"
                style={{ background: shade(c, max) }}
              />
            ))}
            <span className="ml-1">more</span>
          </div>
        </div>
      )}
    </PageShell>
  );
}
