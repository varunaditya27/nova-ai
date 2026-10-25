"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/cn";
import { useReducedMotionSafe } from "@/lib/motion";

/**
 * A note in the margin, in Nova's handwriting: a short aside about the page, tilted a little, with a quick
 * pen-stroke underneath that draws itself once. Always optional reading: nothing here is an instruction.
 */
export function Margin({
  children,
  tilt = -1.5,
  className,
}: {
  children: ReactNode;
  /** Degrees. Notes lean a little differently so a page never looks printed. */
  tilt?: number;
  className?: string;
}) {
  const { reduced } = useReducedMotionSafe();
  return (
    <motion.span
      className={cn(
        "hand relative inline-block origin-left text-accent",
        className,
      )}
      style={{ rotate: tilt }}
      initial={reduced ? false : { opacity: 0, x: -6 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.25 }}
    >
      {children}
      <svg
        aria-hidden
        viewBox="0 0 100 6"
        preserveAspectRatio="none"
        className="absolute -bottom-1 left-0 h-[5px] w-full overflow-visible"
      >
        <motion.path
          d="M1 4 C 18 1, 34 5, 52 3 S 84 2, 99 4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
          initial={reduced ? false : { pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: "easeOut", delay: 0.7 }}
        />
      </svg>
    </motion.span>
  );
}
