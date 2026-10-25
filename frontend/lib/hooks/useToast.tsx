"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence, motion } from "motion/react";
import { springs, useReducedMotionSafe } from "@/lib/motion";

type Toast = { id: number; title: string; detail?: string };

const ToastContext = createContext<{
  toast: (title: string, detail?: string) => void;
}>({
  toast: () => {},
});

/** A quiet acknowledgement for things Nova should confirm without interrupting: a saved moment, a
 * forgotten memory. It floats above the page (so it may cast a shadow) and speaks via aria-live. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const { t } = useReducedMotionSafe();

  const toast = useCallback((title: string, detail?: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, title, detail }]);
    setTimeout(
      () => setToasts((prev) => prev.filter((x) => x.id !== id)),
      5200,
    );
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-4 bottom-24 z-[60] flex flex-col items-center gap-2 lg:inset-x-auto lg:bottom-8 lg:right-8 lg:items-end"
      >
        <AnimatePresence>
          {toasts.map((x) => (
            <motion.div
              key={x.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={t(springs.wake)}
              className="floating pointer-events-auto max-w-sm rounded-2xl px-5 py-4"
            >
              <p className="font-medium">{x.title}</p>
              {x.detail && (
                <p className="mt-1 text-[length:var(--text-small)] text-ink-soft">
                  {x.detail}
                </p>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
