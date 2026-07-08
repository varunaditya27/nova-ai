"use client";

import { motion } from "motion/react";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/** The quiet supporting line — only human verbs, never software ones. */
export function HumanVerbs() {
  const { t } = useReducedMotionSafe();
  return (
    <motion.p
      variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
      transition={t(springs.settle)}
      className="max-w-md text-lg leading-relaxed text-ink-soft"
    >
      It remembers. It notices. It continues — across years, not sessions. A place to think, with
      something that grows to understand you.
    </motion.p>
  );
}
