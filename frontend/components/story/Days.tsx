"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Sheet } from "@/components/ui/Sheet";
import { Skeleton, Trouble } from "@/components/ui/States";
import { searchMessages } from "@/lib/api/client";
import { buildDays, mondayOffset, monthRange, quiltTone } from "@/lib/calendar";
import { useCalendar } from "@/lib/hooks/useLife";
import { cn } from "@/lib/cn";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTH = new Intl.DateTimeFormat("en", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});
const DAY_LONG = new Intl.DateTimeFormat("en", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "UTC",
});

function DaySheet({
  date,
  onClose,
}: {
  date: string | null;
  onClose: () => void;
}) {
  const q = useQuery({
    queryKey: ["day", date],
    queryFn: () =>
      searchMessages("", {
        start: `${date}T00:00:00Z`,
        end: `${date}T23:59:59Z`,
        limit: 100,
      }),
    enabled: Boolean(date),
  });
  const messages = [...(q.data ?? [])].sort((a, b) => a.cursor - b.cursor);
  return (
    <Sheet
      open={Boolean(date)}
      onClose={onClose}
      title={date ? DAY_LONG.format(new Date(`${date}T12:00:00Z`)) : ""}
    >
      {q.isLoading && <Skeleton lines={4} />}
      {q.isError && (
        <Trouble
          what="That day couldn’t be opened just now."
          onRetry={() => q.refetch()}
        />
      )}
      {messages.length > 0 && (
        <>
          <ol className="flex flex-col gap-5">
            {messages.map((m) => (
              <li key={m.message_id}>
                <p className="text-[length:var(--text-small)] text-mute">
                  {m.role === "nova" ? "Nova" : "You"}
                </p>
                <p className="whitespace-pre-wrap">{m.content}</p>
              </li>
            ))}
          </ol>
          <Link
            href={`/?m=${messages[0].message_id}`}
            onClick={onClose}
            className="mt-8 inline-flex min-h-11 items-center self-start cut-sm bg-accent px-6 text-accent-ink"
          >
            Open this day in the conversation
          </Link>
        </>
      )}
    </Sheet>
  );
}

/** Every day as a small square on a quilt: the busier the day, the deeper the colour. Tap a day to reread it. */
export function Days() {
  const now = new Date();
  const [cursor, setCursor] = useState({
    year: now.getUTCFullYear(),
    month: now.getUTCMonth(),
  });
  const [open, setOpen] = useState<string | null>(null);
  const { start, end } = monthRange(cursor.year, cursor.month);
  const q = useCalendar(start, end);

  const days = useMemo(
    () => (q.data ? buildDays(start, end, q.data.days) : []),
    [q.data, start, end],
  );
  const max = Math.max(1, ...days.map((d) => d.count));
  const busiest = days.reduce((a, b) => (b.count > a.count ? b : a), {
    date: "",
    count: 0,
    dow: 0,
  });
  const isCurrent =
    cursor.year === now.getUTCFullYear() && cursor.month === now.getUTCMonth();
  const step = (delta: number) =>
    setCursor((c) => {
      const d = new Date(Date.UTC(c.year, c.month + delta, 1));
      return { year: d.getUTCFullYear(), month: d.getUTCMonth() };
    });
  const total = days.reduce((n, d) => n + d.count, 0);

  return (
    <div className="max-w-3xl">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h2 className="text-[length:var(--text-title)]">
          {MONTH.format(new Date(Date.UTC(cursor.year, cursor.month, 1)))}
        </h2>
        <div className="flex gap-2">
          <button
            aria-label="Previous month"
            onClick={() => step(-1)}
            className="grid size-11 place-items-center cut-sm bg-sunk hover:bg-raised"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            aria-label="Next month"
            disabled={isCurrent}
            onClick={() => step(1)}
            className="grid size-11 place-items-center cut-sm bg-sunk hover:bg-raised disabled:opacity-40"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      {q.isLoading ? (
        <Skeleton lines={5} />
      ) : q.isError ? (
        <Trouble
          what="This month couldn’t be loaded just now."
          onRetry={() => q.refetch()}
        />
      ) : (
        <>
          <div
            className="grid grid-cols-7 gap-1.5 sm:gap-2"
            role="grid"
            aria-label="Days of the month"
          >
            {WEEKDAYS.map((w) => (
              <p
                key={w}
                className="pb-1 text-center text-[length:var(--text-small)] text-mute"
                role="columnheader"
              >
                {w}
              </p>
            ))}
            {days.length > 0 &&
              Array.from({ length: mondayOffset(days[0].dow) }).map((_, i) => (
                <span key={`gap-${i}`} aria-hidden />
              ))}
            {days.map((d) => {
              const tone = quiltTone(d.count, max);
              const day = Number(d.date.slice(8));
              return (
                <button
                  key={d.date}
                  role="gridcell"
                  disabled={d.count === 0}
                  onClick={() => setOpen(d.date)}
                  aria-label={`${DAY_LONG.format(new Date(`${d.date}T12:00:00Z`))}: ${d.count === 0 ? "nothing said" : `${d.count} ${d.count === 1 ? "message" : "messages"}`}`}
                  className={cn(
                    "grid aspect-square place-items-center cut text-[length:var(--text-small)] transition-transform",
                    d.count > 0 && "hover:-translate-y-0.5",
                  )}
                  style={tone}
                >
                  {day}
                </button>
              );
            })}
          </div>
          <p className="read mt-6 text-ink-soft">
            {total === 0
              ? "No conversations this month."
              : `${total} ${total === 1 ? "message" : "messages"} this month. The busiest day was ${DAY_LONG.format(new Date(`${busiest.date}T12:00:00Z`))}.`}
          </p>
        </>
      )}
      <DaySheet date={open} onClose={() => setOpen(null)} />
    </div>
  );
}
