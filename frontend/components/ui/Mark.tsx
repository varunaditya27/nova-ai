"use client";

import type { CSSProperties } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/cn";
import { useReducedMotionSafe } from "@/lib/motion";

type State = "still" | "thinking";

/**
 * Nova's mark: a bookplate. A maroon square with its corner folded over, the way you dog-ear a page you
 * mean to come back to, and a single italic "n" set in it. It is the same stamp on every reply Nova writes
 * (the way a letter is signed), in the sidebar, on the favicon, and as the pressed corner every surface on
 * the site carries. While Nova is writing, it is pressed again and again.
 */
export function Mark({
  size = 24,
  state = "still",
  quiet = false,
  className,
  label,
}: {
  /** Pixels, or any CSS length. */
  size?: number | string;
  state?: State;
  /** Muted, for places where Nova is absent (an error, a page that isn't there). */
  quiet?: boolean;
  className?: string;
  /** Accessible name; omit when purely decorative. */
  label?: string;
}) {
  const { reduced } = useReducedMotionSafe();
  const len = typeof size === "number" ? `${size}px` : size;
  const style = {
    width: len,
    height: len,
    fontSize: `calc(${len} * 0.7)`,
    "--c": `calc(${len} * 0.3)`,
  } as CSSProperties;
  return (
    <motion.span
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={cn(
        "fold inline-grid shrink-0 place-items-center font-display font-bold italic leading-none",
        quiet ? "bg-sunk text-mute" : "bg-accent text-accent-ink",
        className,
      )}
      style={style}
      animate={
        state === "thinking" && !reduced ? { scale: [1, 0.9, 1] } : undefined
      }
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
    >
      <span aria-hidden className="-translate-y-[0.04em]">
        n
      </span>
    </motion.span>
  );
}

/** The name, set plainly: no effects, no ligature, in the display face. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "font-display font-bold leading-none tracking-[-0.02em]",
        className,
      )}
    >
      Nova
    </span>
  );
}

/** The stamp and the name together. */
export function Lockup({
  className,
  state,
}: {
  className?: string;
  state?: State;
}) {
  return (
    <span className={cn("inline-flex items-center gap-[0.35em]", className)}>
      <Mark size="1.05em" state={state} />
      <Wordmark />
    </span>
  );
}
