"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/**
 * A side sheet for looking closer at one thing without leaving the page. Esc closes, focus moves in
 * and returns to whatever opened it, and the page behind stops scrolling. It floats, so it may cast
 * a shadow — nothing resting on the page does.
 */
export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const { t } = useReducedMotionSafe();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
      opener?.focus?.();
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <motion.button
            aria-label="Close"
            className="absolute inset-0 cursor-default bg-ink/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            className="floating relative flex h-full w-full max-w-xl flex-col overflow-y-auto rounded-l-[1.75rem] px-6 pb-10 pt-6 outline-none sm:px-9"
            initial={{ x: 48, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 48, opacity: 0 }}
            transition={t(springs.settle)}
          >
            <div className="mb-6 flex items-start justify-between gap-4">
              <h2 className="text-[length:var(--text-title)]">{title}</h2>
              <button
                onClick={onClose}
                aria-label="Close"
                className="grid size-11 shrink-0 place-items-center cut-sm bg-sunk text-ink hover:bg-surface"
              >
                <X size={18} />
              </button>
            </div>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
