"use client";

import type { ReactNode } from "react";
import { Mark } from "./Mark";
import { Button } from "./Button";
import { cn } from "@/lib/cn";

/** A page with nothing on it yet. It says why, and what to do — silence is a feature, not a void. */
export function Empty({
  title,
  children,
  action,
  className,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "tone flex flex-col items-start gap-4 px-7 py-10 sm:px-10 sm:py-12",
        className,
      )}
    >
      <Mark size={36} />
      <h2 className="max-w-lg text-[length:var(--text-title)]">{title}</h2>
      {children && <p className="read max-w-xl text-ink-soft">{children}</p>}
      {action}
    </div>
  );
}

/** What happened, whether anything is lost, and what to do — never "something went wrong". */
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
      <p className="read max-w-xl">{what}</p>
      <p className="max-w-xl text-ink-soft">
        Nothing you’ve said or saved is lost. This usually clears up on its own.
      </p>
      {onRetry && (
        <Button variant="quiet" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

/** Loading is a calm settle of flat blocks, never a spinner. */
export function Skeleton({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div aria-hidden className={cn("flex flex-col gap-3", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="shimmer h-5 bg-sunk"
          style={{ width: `${88 - i * 14}%` }}
        />
      ))}
    </div>
  );
}
