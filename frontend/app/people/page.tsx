"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { PersonCard } from "@/components/people/PersonCard";
import { usePeople } from "@/lib/hooks/usePeople";

/** People — everyone Nova has learned about from what you've said, never inferred. */
export default function People() {
  const { data, isLoading } = usePeople();

  return (
    <PageShell
      title="People"
      description="Everyone Nova has learned about from what you've told it — nothing guessed."
    >
      {isLoading && <div className="h-40 rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">No one yet — mention someone and Nova will remember them.</p>
      )}
      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((p) => (
            <PersonCard key={p.person_id} person={p} />
          ))}
        </div>
      )}
    </PageShell>
  );
}
