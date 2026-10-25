"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";
import { focusPull, stagger } from "@/lib/motion";
import { Mark } from "./Mark";
import { Margin } from "@/components/brand/Margin";

/**
 * Every inner page: one h1 that says what the page is, one plain sentence that says what it's for,
 * then content. Consistent outer margins; asymmetry lives inside the grid, not the frame.
 */
export function Page({
  title,
  intro,
  note,
  actions,
  children,
}: {
  title: string;
  intro?: ReactNode;
  /** Nova's handwritten aside about this page (see `NOTES` in lib/voice.ts). */
  note?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <motion.div
      variants={stagger(0.12)}
      initial="hidden"
      animate="show"
      className="mx-auto w-full max-w-6xl px-5 pb-28 pt-8 sm:px-8 lg:px-12 lg:pt-14"
    >
      <motion.header
        variants={focusPull}
        className="mb-10 flex flex-wrap items-end justify-between gap-x-8 gap-y-4"
      >
        <div className="max-w-2xl">
          <h1 className="text-[length:clamp(2.25rem,1.2rem+3vw,3.75rem)] leading-[1.02]">
            {title}
          </h1>
          <span aria-hidden className="page-rule mt-5" />
          {intro && <p className="read mt-5 text-ink-soft">{intro}</p>}
          {note && (
            <p className="mt-4 flex items-center gap-2.5">
              <Mark size={22} alive />
              <Margin>{note}</Margin>
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </motion.header>
      <motion.div variants={focusPull}>{children}</motion.div>
    </motion.div>
  );
}
