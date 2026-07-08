"use client";

import { motion } from "motion/react";
import { Surface } from "@/components/primitives/Surface";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/**
 * A thought Nova has been holding (top proactive candidate). Rendered quietly, never as a
 * notification. Hidden entirely when there's nothing waiting — silence is a feature.
 */
export function HeldThought({ thought }: { thought: string | null }) {
  const { t } = useReducedMotionSafe();
  if (!thought) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={t(springs.settle)}
    >
      <Surface className="max-w-lg p-5">
        <p className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
          A thought I&apos;ve been holding
        </p>
        <p className="text-[15px] leading-relaxed text-ink">{thought}</p>
      </Surface>
    </motion.div>
  );
}
