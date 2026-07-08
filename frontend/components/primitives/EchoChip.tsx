"use client";

import { X } from "lucide-react";
import { motion } from "motion/react";
import type { Echo } from "@/lib/api/types";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/**
 * One recalled memory, rendered small and quiet. Dismissible — echoes are ambient, never demanding.
 */
export function EchoChip({ echo, onDismiss }: { echo: Echo; onDismiss: () => void }) {
  const { t } = useReducedMotionSafe();
  return (
    <motion.span
      layout
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={t(springs.wake)}
      className="group/echo inline-flex items-center gap-1.5 rounded-sm border border-hairline bg-surface px-2 py-1 text-[11px]"
      title={echo.created_at ?? undefined}
    >
      <span className="text-ink-soft">{echo.summary}</span>
      <span className="text-ink-faint">· {echo.when}</span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss echo"
        className="ml-0.5 text-ink-faint opacity-0 transition-opacity group-hover/echo:opacity-100 hover:text-ink"
      >
        <X size={11} strokeWidth={2.5} />
      </button>
    </motion.span>
  );
}
