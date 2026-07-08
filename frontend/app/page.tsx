"use client";

import { motion } from "motion/react";
import { Belief } from "@/components/marketing/Belief";
import { HumanVerbs } from "@/components/marketing/HumanVerbs";
import { BeginCTA } from "@/components/marketing/BeginCTA";
import { NovaMark } from "@/components/primitives/NovaMark";
import { useReducedMotionSafe } from "@/lib/motion";

/**
 * The Threshold — the front door. One statement of belief, one line of human verbs, one way in.
 * No feature grid, no gradient, no floating cards. It should make a first-time visitor curious.
 */
export default function Threshold() {
  const { reduced } = useReducedMotionSafe();
  const container = {
    hidden: {},
    show: {
      transition: {
        staggerChildren: reduced ? 0 : 0.12,
        delayChildren: reduced ? 0 : 0.08,
      },
    },
  };

  return (
    <main className="relative z-10 flex min-h-dvh flex-col justify-center px-6 sm:px-10">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mx-auto flex w-full max-w-2xl flex-col gap-8"
      >
        {/* The one brass moment on the threshold — the wordmark. */}
        <motion.div
          variants={{ hidden: { opacity: 0 }, show: { opacity: 1 } }}
          className="flex items-center gap-2.5"
        >
          <span className="text-brass">
            <NovaMark size={20} title="Nova" />
          </span>
          <span className="font-display text-sm tracking-wide text-ink">Nova</span>
        </motion.div>

        <Belief />
        <HumanVerbs />
        <BeginCTA />

        <motion.p
          variants={{ hidden: { opacity: 0 }, show: { opacity: 1 } }}
          className="mt-10 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-faint"
        >
          A private study for thinking
        </motion.p>
      </motion.div>
    </main>
  );
}
