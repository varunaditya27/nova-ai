"use client";

import { motion } from "motion/react";
import { useReducedMotionSafe } from "@/lib/motion";

type State = "still" | "idle" | "thinking";

/**
 * Nova's mark and presence: a flat four-pointed star. It is the same shape everywhere — the nav,
 * Nova's name on a reply, the "thinking" indicator — and only its behaviour changes: still, a slow
 * breath at rest, a slow turn while Nova is working on a reply. No glow, no bounce.
 */
export function Ember({
  size = 24,
  state = "still",
  className,
  label,
}: {
  size?: number;
  state?: State;
  className?: string;
  /** Accessible name; omit when purely decorative. */
  label?: string;
}) {
  const { reduced } = useReducedMotionSafe();
  const animate =
    reduced || state === "still"
      ? undefined
      : state === "thinking"
        ? { rotate: [0, 90, 180, 270, 360], scale: [1, 0.86, 1, 0.86, 1] }
        : { scale: [1, 1.08, 1] };
  const transition =
    state === "thinking"
      ? { duration: 2.8, repeat: Infinity, ease: "linear" as const }
      : { duration: 5, repeat: Infinity, ease: "easeInOut" as const };

  return (
    <motion.svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={className}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      animate={animate}
      transition={transition}
    >
      <path
        fill="currentColor"
        d="M12 0C12.9 7.2 16.8 11.1 24 12 16.8 12.9 12.9 16.8 12 24 11.1 16.8 7.2 12.9 0 12 7.2 11.1 11.1 7.2 12 0Z"
      />
    </motion.svg>
  );
}
