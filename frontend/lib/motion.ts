"use client";

import { useReducedMotion, type Transition } from "motion/react";

/*
 * Motion grammar — springs only, no CSS easing. Content settles; it never flies or overshoots.
 * These three presets cover the whole app: enter (settle), hover (wake), press (tactile).
 */
export const springs = {
  settle: { type: "spring", stiffness: 210, damping: 30, mass: 0.9 },
  wake: { type: "spring", stiffness: 300, damping: 26 },
  press: { type: "spring", stiffness: 520, damping: 30 },
} satisfies Record<string, Transition>;

const instant: Transition = { duration: 0 };

/**
 * Single accessibility chokepoint: wrap any spring with `t(...)` and it collapses to an instant
 * transition when the visitor prefers reduced motion.
 */
export function useReducedMotionSafe() {
  const reduced = useReducedMotion();
  return {
    reduced: Boolean(reduced),
    t: (spring: Transition): Transition => (reduced ? instant : spring),
  };
}
