"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { SavedMessage } from "@/components/vault/SavedMessage";
import { useAnnotate, useMilestones } from "@/lib/hooks/useVault";

/** Milestones — life moments promoted from the thread. An album, oldest first. */
export default function Milestones() {
  const { data, isLoading } = useMilestones();
  const { milestone } = useAnnotate();

  return (
    <PageShell title="Milestones" description="The moments you marked as they happened — an album of your life together.">
      {isLoading && <div className="h-20 rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">No milestones yet. Mark a moment in chat when it matters.</p>
      )}
      <div className="flex flex-col gap-3">
        {data?.map((m) => (
          <SavedMessage
            key={m.message_id}
            message={m}
            tag={m.milestone_label ?? "milestone"}
            tagBrass
            onRemove={() => milestone.mutate({ id: m.message_id, on: false })}
          />
        ))}
      </div>
    </PageShell>
  );
}
