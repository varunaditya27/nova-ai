"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { PageShell } from "@/components/primitives/PageShell";
import { LifeNav } from "@/components/life/LifeNav";
import { useCalendar } from "@/lib/hooks/useLife";
import { buildDays, shade } from "@/lib/calendar";

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

function monthStart(offset = 0): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + offset, 1));
}

/** The Calendar — a warm activity heatmap, navigable month by month. */
export default function Calendar() {
  const [month, setMonth] = useState(() => monthStart(0));
  const start = month.toISOString();
  const end = new Date(
    Date.UTC(month.getUTCFullYear(), month.getUTCMonth() + 1, 0, 23, 59, 59)
  ).toISOString();
  const { data, isLoading } = useCalendar(start, end);

  const days = data ? buildDays(data.start, data.end, data.days) : [];
  const max = Math.max(1, ...days.map((d) => d.count));
  const lead = days.length ? days[0].dow : 0;
  const label = month.toLocaleDateString("en", { month: "long", year: "numeric", timeZone: "UTC" });
  const isCurrentMonth = month.getTime() >= monthStart(0).getTime();

  return (
    <PageShell title="The calendar" description="Every day you and Nova spent together.">
      <LifeNav />
      <div className="mb-5 flex items-center gap-3">
        <button
          onClick={() => setMonth(new Date(Date.UTC(month.getUTCFullYear(), month.getUTCMonth() - 1, 1)))}
          aria-label="Previous month"
          className="rounded-md p-1 text-ink-soft transition-colors hover:text-ink"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="min-w-[9rem] font-mono text-[12px] uppercase tracking-widest text-ink-soft">
          {label}
        </span>
        <button
          onClick={() => setMonth(new Date(Date.UTC(month.getUTCFullYear(), month.getUTCMonth() + 1, 1)))}
          disabled={isCurrentMonth}
          aria-label="Next month"
          className="rounded-md p-1 text-ink-soft transition-colors hover:text-ink disabled:opacity-30"
        >
          <ChevronRight size={16} />
        </button>
      </div>
      {isLoading && <div className="h-40 max-w-xs rounded-md bg-hairline/30" />}
      {data && (
        <div>
          <div
            role="img"
            aria-label={`Activity heatmap for ${label}`}
            className="grid max-w-[320px] grid-cols-7 gap-1.5"
          >
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
