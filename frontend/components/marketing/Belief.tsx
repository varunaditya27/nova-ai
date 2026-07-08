"use client";

import { motion } from "motion/react";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/** The statement of belief — set large in Fraunces, at a display optical size. */
export function Belief() {
  const { t } = useReducedMotionSafe();
  return (
    <motion.h1
      variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
      transition={t(springs.settle)}
      className="text-balance font-display text-4xl leading-[1.08] tracking-[-0.02em] text-ink sm:text-5xl md:text-[3.4rem]"
      style={{ fontVariationSettings: '"opsz" 96, "SOFT" 24, "wght" 400' }}
    >
      Intelligence should feel like a relationship, not a tool.
    </motion.h1>
  );
}
