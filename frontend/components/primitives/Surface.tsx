"use client";

import type { ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { cn } from "@/lib/cn";
import { springs, useReducedMotionSafe } from "@/lib/motion";

type SurfaceProps = HTMLMotionProps<"div"> & {
  /** Start already lifted (bg-raised) instead of bg-surface. */
  raised?: boolean;
  /** Disable the hover-wake (for purely static panels). */
  interactive?: boolean;
};

/**
 * A carved panel. On cursor approach it "wakes" — a bg-raised layer springs in and a 1px inner
 * highlight appears. Depth comes from contrast, never a drop shadow.
 */
export function Surface({
  raised = false,
  interactive = true,
  className,
  children,
  ...rest
}: SurfaceProps) {
  const { t } = useReducedMotionSafe();
  return (
    <motion.div
      initial="rest"
      whileHover={interactive ? "wake" : undefined}
      className={cn(
        "relative rounded-md border border-hairline",
        raised ? "bg-raised" : "bg-surface",
        className
      )}
      {...rest}
    >
      {interactive && (
        <motion.span
          aria-hidden
          variants={{ rest: { opacity: 0 }, wake: { opacity: 1 } }}
          transition={t(springs.wake)}
          className="pointer-events-none absolute inset-0 rounded-md bg-raised"
          style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
        />
      )}
      <div className="relative">{children as ReactNode}</div>
    </motion.div>
  );
}
