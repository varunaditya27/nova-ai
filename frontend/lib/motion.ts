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

/*
 * Nova's motion identity. One personality — warm, unhurried, never bouncy — carried by one signature
 * curve (about 80% of everything), a three-step duration palette, and one entrance (rise, then settle).
 * Every scene has three layers: the main action, a supporting detail, and a slow ambient life.
 */
export const nova = {
  /** Entrances decelerate: fast out of the gate, a long gentle landing. Nothing overshoots. */
  ease: [0.16, 1, 0.3, 1] as const,
  /** Moves between two on-screen states, and anything ambient, ease both ends. */
  move: [0.4, 0, 0.2, 1] as const,
  gsapEase: "power4.out",
  gsapMove: "power2.inOut",
  /** Seconds. Quick for state changes, standard for cards, slow for reveals that carry meaning. */
  dur: { quick: 0.35, standard: 0.5, slow: 0.8 },
} as const;

/** The entrance pattern: slightly low, slightly small and out of focus, then settled and sharp. Used everywhere on the landing page. */
export const focusPull: Variants = {
  hidden: { opacity: 0, y: 28, scale: 0.98, filter: "blur(8px)" },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: { duration: nova.dur.slow + 0.2, ease: nova.ease },
  },
};
