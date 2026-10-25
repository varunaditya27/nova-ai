"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";
import { focusPull } from "@/lib/motion";

/** Nova's one entrance, used on every page: it settles from slightly low, small and out of focus the first time it scrolls into view. */
export function Reveal({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      variants={focusPull}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "0px 0px -8% 0px" }}
    >
      {children}
    </motion.div>
  );
}
