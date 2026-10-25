"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";
import { rise } from "@/lib/motion";
import { cn } from "@/lib/cn";

const TONES = { ground: "", sunk: "bg-sunk", ink: "bg-ink text-ground" } as const;

/** One band of the page: a full-width tone, with content held to the same column as every other page. */
export function Section({
  id,
  tone = "ground",
  label,
  children,
  className,
}: {
  id?: string;
  tone?: keyof typeof TONES;
  /** Accessible name; the section's visible heading should be what this says. */
  label?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} aria-label={label} className={cn("scroll-mt-16 px-5 py-20 sm:px-8 sm:py-28 lg:px-12", TONES[tone])}>
      <div className={cn("mx-auto max-w-6xl", className)}>{children}</div>
    </section>
  );
}

/** Settles into place the first time it scrolls into view. Reduced-motion users see it immediately. */
export function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      variants={rise}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "0px 0px -8% 0px" }}
    >
      {children}
    </motion.div>
  );
}
