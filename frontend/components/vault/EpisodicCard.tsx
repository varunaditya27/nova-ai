"use client";

import { useState } from "react";
import { Surface } from "@/components/primitives/Surface";
import { Meter } from "@/components/primitives/Meter";
import { useDeleteMemory } from "@/lib/hooks/useVault";
import { relativeTime } from "@/lib/time";
import type { MemoryOut } from "@/lib/api/types";

/** One episodic memory, with a deliberate two-step "forget" (Layer-12 selective deletion). */
export function EpisodicCard({ memory }: { memory: MemoryOut }) {
  const del = useDeleteMemory();
  const [confirming, setConfirming] = useState(false);

  return (
    <Surface className="p-5">
      <p className="text-[15px] leading-relaxed text-ink">{memory.summary}</p>
      <div className="mt-3 flex items-center gap-3">
        <Meter value={memory.importance} className="max-w-[120px] flex-1" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          {relativeTime(memory.created_at)}
        </span>
      </div>
      {memory.topic_tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {memory.topic_tags.map((tag) => (
            <span
              key={tag}
              className="rounded-sm border border-hairline px-1.5 py-0.5 text-[11px] text-ink-soft"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
      <div className="mt-3">
        {confirming ? (
          <span className="inline-flex items-center gap-3 text-sm text-ink-soft">
            Forget this — permanently?
            <button
              onClick={() => del.mutate(memory.memory_id)}
              disabled={del.isPending}
              className="font-medium text-brass hover:underline"
            >
              Yes, forget
            </button>
            <button onClick={() => setConfirming(false)} className="text-ink-faint hover:text-ink">
              Keep
            </button>
          </span>
        ) : (
          <button
            onClick={() => setConfirming(true)}
            className="font-mono text-[11px] uppercase tracking-widest text-ink-faint transition-colors hover:text-ink-soft"
          >
            Forget
          </button>
        )}
      </div>
    </Surface>
  );
}
