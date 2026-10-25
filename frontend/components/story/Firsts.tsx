"use client";

import { Empty, Skeleton, Trouble } from "@/components/ui/States";
import { useMuseum } from "@/lib/hooks/useLife";
import { longDate } from "@/lib/time";

/** The things people cherish for no practical reason: the first time. Marigold marks the earned. */
export function Firsts() {
  const q = useMuseum();
  if (q.isLoading) return <Skeleton lines={3} />;
  if (q.isError)
    return (
      <Trouble
        what="Your firsts couldn’t be loaded just now."
        onRetry={() => q.refetch()}
      />
    );
  const entries = q.data?.entries ?? [];
  if (entries.length === 0) {
    return (
      <Empty title="Nothing here yet — everything is still ahead.">
        Your first conversation, your first goal, the first moment you mark as
        mattering: each one is kept here, with the day it happened.
      </Empty>
    );
  }
  return (
    <ul className="flex flex-col gap-10">
      {entries.map((e) => (
        <li
          key={e.label}
          className="grid gap-3 md:grid-cols-[13rem_1fr] md:gap-8"
        >
          <div>
            <p className="inline-flex items-center gap-2 text-[length:var(--text-read)]">
              <span aria-hidden className="size-3 rounded-full bg-earned" />
              {e.label}
            </p>
            {e.when && (
              <p className="mt-1 text-[length:var(--text-small)] text-ink-soft">
                {longDate(e.when)}
              </p>
            )}
          </div>
          {e.content && (
            <blockquote className="font-display text-[length:var(--text-title)] leading-[1.15]">
              “{e.content}”
            </blockquote>
          )}
        </li>
      ))}
    </ul>
  );
}
