"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";
import { springs, useReducedMotionSafe } from "@/lib/motion";

/** Shared layout for every lens page: a Fraunces title, optional description, and a settling body. */
export function PageShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  const { t } = useReducedMotionSafe();
  return (
    <main className="relative z-10 mx-auto max-w-2xl px-6 pb-32 pt-20 sm:px-10">
      <motion.header
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={t(springs.settle)}
      >
        <h1
          className="font-display text-3xl tracking-[-0.01em] text-ink"
          style={{ fontVariationSettings: '"opsz" 60, "SOFT" 30, "wght" 400' }}
        >
          {title}
        </h1>
        {description && <p className="mt-2 max-w-lg text-ink-soft">{description}</p>}
      </motion.header>
      <div className="mt-8">{children}</div>
    </main>
  );
}
