"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { LifeNav } from "@/components/life/LifeNav";
import { useSummaries } from "@/lib/hooks/useLife";

function fmtRange(start: string | null, end: string | null): string {
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  const s = start ? new Date(start).toLocaleDateString("en", opts) : "";
  const e = end ? new Date(end).toLocaleDateString("en", opts) : "";
  return s && e ? `${s} – ${e}` : s || e;
}

/** The Timeline — weekly chapters as a vertical thread down the page. */
export default function Life() {
  const { data, isLoading } = useSummaries();
  return (
    <PageShell title="Your life together" description="The story so far, one week at a time.">
      <LifeNav />
      {isLoading && <div className="h-24 max-w-md rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">No chapters yet. They form as the weeks accumulate.</p>
      )}
      {data && data.length > 0 && (
        <ol className="relative border-l border-hairline pl-6">
          {data.map((s) => (
            <li key={s.summary_id} className="relative mb-8 last:mb-0">
              <span className="absolute -left-[27px] top-1.5 h-2 w-2 rounded-full bg-ink-faint" />
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
                {fmtRange(s.week_start_date, s.week_end_date)} · {s.session_count} session
                {s.session_count === 1 ? "" : "s"}
              </p>
              {s.dominant_theme && (
                <p className="mt-1 font-display text-lg text-ink">{s.dominant_theme}</p>
              )}
              <p className="mt-1 max-w-lg leading-relaxed text-ink-soft">{s.week_narrative}</p>
            </li>
          ))}
        </ol>
      )}
    </PageShell>
  );
}
