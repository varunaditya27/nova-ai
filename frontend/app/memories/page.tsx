"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { Meter } from "@/components/primitives/Meter";
import { IntegrityBadge } from "@/components/vault/IntegrityBadge";
import { EpisodicCard } from "@/components/vault/EpisodicCard";
import { useMemoryAudit } from "@/lib/hooks/useVault";

/** The vault — episodic memories (forgettable) and the stable facts distilled from them. */
export default function Memories() {
  const { data, isLoading } = useMemoryAudit();
  return (
    <PageShell
      title="What Nova remembers"
      description="Moments it kept, and the stable facts it drew from them. Nothing here is hidden from you."
    >
      <div className="mb-8">
        <IntegrityBadge />
      </div>

      {isLoading && <div className="h-24 rounded-md bg-hairline/30" />}

      {data && (
        <div className="flex flex-col gap-8">
          <section>
            <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
              moments · {data.episodic.length}
            </p>
            {data.episodic.length === 0 ? (
              <p className="text-ink-soft">Nothing kept yet.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {data.episodic.map((m) => (
                  <EpisodicCard key={m.memory_id} memory={m} />
                ))}
              </div>
            )}
          </section>

          {data.semantic.length > 0 && (
            <section>
              <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                what it understands · {data.semantic.length}
              </p>
              <div className="flex flex-col gap-3">
                {data.semantic.map((s) => (
                  <Surface key={s.memory_id} className="p-5">
                    <p className="text-[15px] leading-relaxed text-ink">{s.statement}</p>
                    <Meter value={s.confidence} className="mt-3 max-w-[160px]" />
                  </Surface>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </PageShell>
  );
}
