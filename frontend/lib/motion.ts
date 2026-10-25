"use client";

import { useReducedMotion, type Transition, type Variants } from "motion/react";

/*
 * Motion grammar: confidently unhurried. Springs are critically damped (damping ratio >= 1) so
 * nothing bounces or overshoots; content settles. Only transform and opacity ever animate.
 */
export const springs = {
  settle: { type: "spring", stiffness: 170, damping: 28, mass: 1 }, // ratio ~1.07
  wake: { type: "spring", stiffness: 300, damping: 35 }, // ratio ~1.01
  press: { type: "spring", stiffness: 520, damping: 46 }, // ratio ~1.0
} satisfies Record<string, Transition>;

const instant: Transition = { duration: 0 };

/** Single accessibility chokepoint: collapses any transition to instant for reduced-motion users. */
export function useReducedMotionSafe() {
  const reduced = useReducedMotion();
  return {
    reduced: Boolean(reduced),
    t: (spring: Transition): Transition => (reduced ? instant : spring),
  };
}

/** Entrance: rise 20px while fading in. Stagger children by ~70ms via `staggerChildren`. */
export const rise: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: springs.settle },
};

export const stagger = (gap = 0.07, delay = 0): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: gap, delayChildren: delay } },
});
