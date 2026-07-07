"use client";

import { motion, type HTMLMotionProps } from "motion/react";
import { cn } from "@/lib/cn";
import { springs, useReducedMotionSafe } from "@/lib/motion";
import { useAcoustics } from "@/lib/hooks/useAcoustics";

type CarvedButtonProps = HTMLMotionProps<"button"> & {
  /** `brass` is earned-only — reserve it for milestones / firsts / bookmarks. */
  variant?: "default" | "brass";
};

/**
 * A button that feels carved: a subtle inner highlight, a hairline stroke, and a tactile spring
 * on press. Plays the paper-click on activation (silent when acoustics are muted).
 */
export function CarvedButton({
  variant = "default",
  className,
  onClick,
  children,
  ...rest
}: CarvedButtonProps) {
  const { play } = useAcoustics();
  const { t } = useReducedMotionSafe();
  return (
    <motion.button
      whileTap={{ scale: 0.98 }}
      transition={t(springs.press)}
      onClick={(e) => {
        play("click");
        onClick?.(e);
      }}
      style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
      className={cn(
        "inline-flex select-none items-center justify-center gap-2 rounded-md border px-4 py-2",
        "text-sm font-medium transition-colors",
        variant === "brass"
          ? "border-brass/40 text-brass hover:bg-brass/5"
          : "border-hairline bg-surface text-ink hover:bg-raised",
        className
      )}
      {...rest}
    >
      {children}
    </motion.button>
  );
}
