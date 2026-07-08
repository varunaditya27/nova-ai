"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/cn";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/**
 * A single turn in the conversation — deliberately NOT a bubble. The speaker is named in Fraunces,
 * the text breathes beneath it, and the timestamp only surfaces on hover. "Like iMessage mixed
 * with Medium."
 */
export function ThreadLine({
  role,
  timestamp,
  children,
}: {
  role: "user" | "nova";
  timestamp?: string;
  children: ReactNode;
}) {
  const { t } = useReducedMotionSafe();
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={t(springs.settle)}
      className="group py-5"
    >
      <div className="mb-1.5 flex items-baseline gap-3">
        <span
          className={cn(
            "font-display text-sm",
            role === "nova" ? "text-ink" : "text-ink-soft"
          )}
        >
          {role === "nova" ? "Nova" : "You"}
        </span>
        {timestamp && (
          <span className="font-mono text-[11px] text-ink-faint opacity-0 transition-opacity duration-200 group-hover:opacity-100">
            {timestamp}
          </span>
        )}
      </div>
      <div className="max-w-prose text-[15px] leading-relaxed text-ink [word-break:break-word]">
        {children}
      </div>
    </motion.div>
  );
}
