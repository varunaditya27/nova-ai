"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/cn";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/**
 * A thin horizontal meter. `brass` marks an earned state (a completed goal); otherwise ink-soft.
 * Optional pole labels turn it into a preference dial (casual ↔ formal, terse ↔ verbose).
 */
export function Meter({
  value,
  brass = false,
  leftLabel,
  rightLabel,
  className,
}: {
  value: number;
  brass?: boolean;
  leftLabel?: string;
  rightLabel?: string;
  className?: string;
}) {
  const { t } = useReducedMotionSafe();
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const ariaLabel =
    leftLabel && rightLabel ? `${leftLabel} to ${rightLabel}` : "progress";
  return (
    <div className={className}>
      <div
        role="meter"
        aria-label={ariaLabel}
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-1.5 w-full overflow-hidden rounded-full bg-hairline"
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: brass ? "var(--brass)" : "var(--ink-soft)" }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={t(springs.settle)}
        />
      </div>
      {(leftLabel || rightLabel) && (
        <div className="mt-1 flex justify-between font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          <span>{leftLabel}</span>
          <span className={cn(!rightLabel && "hidden")}>{rightLabel}</span>
        </div>
      )}
    </div>
  );
}
