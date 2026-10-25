"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Mark } from "./Mark";
import { Margin } from "@/components/brand/Margin";
import { EMPTY, OOPS, waitingLine, type EmptyKey } from "@/lib/voice";
import { Button } from "./Button";
import { cn } from "@/lib/cn";

/** A page with nothing on it yet. Nova says why, in its own voice, and what to do: silence is a feature, not a void. */
export function Empty({
  kind,
  action,
  className,
}: {
  kind: EmptyKey;
  action?: ReactNode;
  className?: string;
}) {
  const { title, body, note } = EMPTY[kind];
  return (
    <div
      className={cn(
        "tone flex flex-col items-start gap-4 px-7 py-10 sm:px-10 sm:py-12",
        className,
      )}
    >
      <span className="flex items-end gap-3">
        <Mark size={40} alive />
        <Margin tilt={-3} className="pb-1">
          {note}
        </Margin>
      </span>
      <h2 className="max-w-lg text-[length:var(--text-title)]">{title}</h2>
      <p className="read max-w-xl text-ink-soft">{body}</p>
      {action}
    </div>
  );
}

/** What happened, whether anything is lost, and what to do. Never "something went wrong", never a joke. */
export function Trouble({
  what,
  onRetry,
}: {
  what: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="tone-sunk flex flex-col items-start gap-4 px-7 py-8"
    >
      <span className="flex items-end gap-3">
        <Mark size={32} mood="lost" quiet />
        <Margin tilt={-2} className="pb-0.5">
          {OOPS.generic}
        </Margin>
      </span>
      <p className="read max-w-xl">{what}</p>
      <p className="max-w-xl text-ink-soft">{OOPS.saved}</p>
      {onRetry && (
        <Button variant="quiet" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

/** Loading is a calm settle of flat blocks, never a spinner, with a line about what Nova is doing meanwhile. */
export function Skeleton({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  const [seed, setSeed] = useState(0);
  // Nova narrates what it is doing, and moves on to another line if the wait is long.
  useEffect(() => {
    const t = setInterval(() => setSeed((n) => n + 1), 3200);
    return () => clearInterval(t);
  }, []);
  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <p role="status" className="hand flex items-center gap-2 text-mute">
        <Mark size={18} mood="thinking" />
        {waitingLine(seed)}
      </p>
      <div aria-hidden className="flex flex-col gap-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="shimmer h-5 bg-sunk"
            style={{ width: `${88 - i * 14}%` }}
          />
        ))}
      </div>
    </div>
  );
}
