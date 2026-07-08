"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { useProactive } from "@/lib/hooks/useNovaState";

/** On Nova's mind — threads it's holding, waiting for the right moment. */
export default function Proactive() {
  const { data, isLoading } = useProactive();
  return (
    <PageShell
      title="On Nova's mind"
      description="Threads it's holding, waiting for the right moment to bring them up."
    >
      {isLoading && <div className="h-20 rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">Nothing right now. Nova only reaches out when it means something.</p>
      )}
      <div className="flex flex-col gap-3">
        {data?.map((p) => (
          <Surface key={p.item_id} className="p-5">
            <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
              {p.item_type.replace(/_/g, " ")}
            </p>
            <p className="text-[15px] leading-relaxed text-ink">{p.content_basis}</p>
          </Surface>
        ))}
      </div>
    </PageShell>
  );
}
