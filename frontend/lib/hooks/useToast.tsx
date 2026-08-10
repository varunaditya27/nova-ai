"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { springs, useReducedMotionSafe } from "@/lib/motion";

type Toast = { id: number; title: string; detail?: string };

const ToastContext = createContext<{ toast: (title: string, detail?: string) => void }>({
  toast: () => {},
});

/** A quiet toast stack, bottom-right above the dock. Used for confirmations Nova should acknowledge
 * without interrupting the flow (a forget certificate, a job result). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const { t: safeTransition } = useReducedMotionSafe();

  const toast = useCallback((title: string, detail?: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, title, detail }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4800);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed bottom-24 right-6 z-[60] flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={safeTransition(springs.wake)}
              className="pointer-events-auto max-w-xs rounded-md border border-hairline bg-raised px-4 py-3"
              style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
            >
              <p className="text-sm text-ink">{t.title}</p>
              {t.detail && (
                <p className="mt-1 break-all font-mono text-[10px] text-ink-faint">{t.detail}</p>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
