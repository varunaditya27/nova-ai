"use client";

import { useParams } from "next/navigation";
import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { Meter } from "@/components/primitives/Meter";
import { usePerson } from "@/lib/hooks/usePeople";

export default function PersonDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = usePerson(id);

  return (
    <PageShell title={data?.display_name ?? "Person"} description={data?.relationship_type.replace(/_/g, " ")}>
      {isLoading && <div className="h-40 rounded-md bg-hairline/30" />}
      {data && (
        <div className="flex flex-col gap-8">
          <Meter
            value={(data.relationship_valence + 1) / 2}
            brass={data.is_support_source}
            leftLabel="strained"
            rightLabel="warm"
          />

          {data.active_patterns.length > 0 && (
            <div>
              <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                patterns
              </p>
              <div className="flex flex-col gap-2">
                {data.active_patterns.map((p) => (
                  <Surface key={p.pattern_id} className="p-4">
                    <p className="text-[15px] text-ink">{p.plain_language_description}</p>
                  </Surface>
                ))}
              </div>
            </div>
          )}

          <div>
            <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
              timeline · {data.recent_events.length}
            </p>
            {data.recent_events.length === 0 && (
              <p className="text-ink-soft">Nothing recorded yet.</p>
            )}
            <div className="flex flex-col gap-2">
              {data.recent_events.map((e) => (
                <Surface key={e.event_id} className="p-4">
                  <p className="text-[15px] text-ink">{e.summary}</p>
                  <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                    {e.event_type.replace(/_/g, " ")}
                    {e.is_resolved ? " · resolved" : ""}
                  </p>
                </Surface>
              ))}
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
