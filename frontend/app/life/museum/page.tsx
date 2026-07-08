"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { LifeNav } from "@/components/life/LifeNav";
import { Surface } from "@/components/primitives/Surface";
import { useMuseum } from "@/lib/hooks/useLife";
import { relativeTime } from "@/lib/time";

/** The Museum — "firsts", the earned moments a relationship is built from. Brass belongs here. */
export default function Museum() {
  const { data, isLoading } = useMuseum();
  return (
    <PageShell title="The museum" description="Firsts, kept — the moments a relationship is built from.">
      <LifeNav />
      {isLoading && <div className="h-24 rounded-md bg-hairline/30" />}
      {data && data.entries.length === 0 && (
        <p className="text-ink-soft">No firsts yet. They&rsquo;re coming.</p>
      )}
      <div className="flex flex-col gap-3">
        {data?.entries.map((e, i) => (
          <Surface key={`${e.label}-${i}`} className="p-5">
            <p
              className="font-display text-brass"
              style={{ fontVariationSettings: '"opsz" 40, "SOFT" 40, "wght" 460' }}
            >
              {e.label}
            </p>
            <p className="mt-1.5 text-[15px] leading-relaxed text-ink">{e.content}</p>
            {e.when && (
              <p className="mt-2 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                {relativeTime(e.when)}
              </p>
            )}
          </Surface>
        ))}
      </div>
    </PageShell>
  );
}
