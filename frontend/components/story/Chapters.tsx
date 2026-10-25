"use client";

import { Empty, Skeleton, Trouble } from "@/components/ui/States";
import { useSummaries } from "@/lib/hooks/useLife";
import { weekRange } from "@/lib/time";

/** Each week, written up as a chapter: its theme, and what happened, in Nova's voice. */
export function Chapters() {
  const q = useSummaries();
  if (q.isLoading) return <Skeleton lines={4} />;
  if (q.isError)
    return (
      <Trouble
        what="Your chapters couldn’t be loaded just now."
        onRetry={() => q.refetch()}
      />
    );
  const chapters = q.data ?? [];
  if (chapters.length === 0) {
    return (
      <Empty kind="chapters" />
    );
  }
  return (
    <ol className="relative flex flex-col gap-14">
      <span
        aria-hidden
        className="absolute bottom-2 left-[7px] top-3 w-[3px] bg-sunk"
      />
      {chapters.map((c, i) => (
        <li
          key={c.summary_id}
          className="relative grid gap-3 pl-10 md:grid-cols-[11rem_1fr] md:gap-8 md:pl-12"
        >
          <span
            aria-hidden
            className={`absolute left-0 top-2 size-[17px] ${i === 0 ? "bg-accent" : "bg-ink-soft"}`}
          />
          <div>
            <p className="text-ink-soft">
              {weekRange(c.week_start_date, c.week_end_date)}
            </p>
            <p className="text-[length:var(--text-small)] text-mute">
              {c.session_count}{" "}
              {c.session_count === 1 ? "conversation" : "conversations"}
            </p>
            {i === 0 && (
              <p className="mt-1 text-[length:var(--text-small)] text-accent">
                Most recent
              </p>
            )}
          </div>
          <div className="max-w-2xl">
            <h2
              className={
                i === 0
                  ? "text-[length:var(--text-title)]"
                  : "text-[length:var(--text-read)]"
              }
            >
              {c.dominant_theme || "A quiet week"}
            </h2>
            <p className="read mt-3">{c.week_narrative}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
