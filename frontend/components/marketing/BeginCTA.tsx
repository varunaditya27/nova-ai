"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { motion } from "motion/react";
import { springs, useReducedMotionSafe } from "@/lib/motion";
import { useAcoustics } from "@/lib/hooks/useAcoustics";

/** The single, restrained way in. A carved link — not a loud button. */
export function BeginCTA() {
  const { play } = useAcoustics();
  const { t } = useReducedMotionSafe();
  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
      transition={t(springs.settle)}
    >
      <Link
        href="/desk"
        onClick={() => play("click")}
        style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
        className="group inline-flex items-center gap-2 rounded-md border border-hairline bg-surface px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-raised"
      >
        Begin
        <ArrowRight
          size={15}
          className="transition-transform duration-300 group-hover:translate-x-0.5"
        />
      </Link>
    </motion.div>
  );
}
