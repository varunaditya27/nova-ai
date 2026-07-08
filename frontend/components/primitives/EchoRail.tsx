"use client";

import { useState } from "react";
import { AnimatePresence } from "motion/react";
import type { Echo } from "@/lib/api/types";
import { EchoChip } from "./EchoChip";

/**
 * The rail of echoes under a Nova turn. Renders nothing when there are none (confabulation guard) —
 * we NEVER invent echoes. Each chip is individually dismissible; when all are gone, so is the rail.
 */
export function EchoRail({ echoes }: { echoes: Echo[] }) {
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const visible = echoes
    .map((echo, i) => ({ echo, i }))
    .filter(({ i }) => !dismissed.has(i));

  if (visible.length === 0) return null;

  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
      <span className="mr-0.5 font-mono text-[10px] uppercase tracking-[0.15em] text-ink-faint">
        echoes
      </span>
      <AnimatePresence initial={false}>
        {visible.map(({ echo, i }) => (
          <EchoChip
            key={i}
            echo={echo}
            onDismiss={() => setDismissed((prev) => new Set(prev).add(i))}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
