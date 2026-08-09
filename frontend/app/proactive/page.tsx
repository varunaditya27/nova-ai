"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { useProactive } from "@/lib/hooks/useNovaState";
import { useProactiveStream } from "@/lib/hooks/useProactiveStream";
import { mergeProactiveItems } from "@/lib/proactive/merge";

/** On Nova's mind — threads it's holding, waiting for the right moment.
 *
 * Only ever renders `message` (the real, SC-4-generated, validated text) -- never
 * `content_basis`, which is an internal fragment (e.g. "Goal: X | Milestone: Y") that was never
 * meant to be read as something Nova said. Items without a generated message yet (the background
 * job hasn't caught up) are simply not shown. `useProactiveStream` pushes new items live via SSE
 * on top of the polled baseline, deduplicated by item_id (see lib/proactive/merge.ts). */
export default function Proactive() {
  const { data, isLoading } = useProactive();
  const streamed = useProactiveStream();
  const shown = mergeProactiveItems(data ?? [], streamed);

  return (
    <PageShell
      title="On Nova's mind"
      description="Threads it's holding, waiting for the right moment to bring them up."
    >
      {isLoading && <div className="h-20 rounded-md bg-hairline/30" />}
      {!isLoading && shown.length === 0 && (
        <p className="text-ink-soft">Nothing right now. Nova only reaches out when it means something.</p>
      )}
      <div className="flex flex-col gap-3">
        {shown.map((p) => (
          <Surface key={p.item_id} className="p-5">
            <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
              {p.item_type.replace(/_/g, " ")}
            </p>
            <p className="text-[15px] leading-relaxed text-ink">{p.message}</p>
          </Surface>
        ))}
      </div>
    </PageShell>
  );
}
