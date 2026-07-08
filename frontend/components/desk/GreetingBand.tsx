"use client";

import { motion } from "motion/react";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/** The greeting — the first thing on the Desk, set in Fraunces. */
export function GreetingBand({ greeting }: { greeting: string }) {
  const { t } = useReducedMotionSafe();
  return (
    <motion.h1
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={t(springs.settle)}
      className="font-display text-3xl tracking-[-0.01em] text-ink sm:text-4xl"
      style={{ fontVariationSettings: '"opsz" 72, "SOFT" 30, "wght" 380' }}
    >
      {greeting}.
    </motion.h1>
  );
}
