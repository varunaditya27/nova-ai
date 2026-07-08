"use client";

import { usePendingTools } from "@/lib/hooks/useTools";
import { ToolConfirmationCard } from "@/components/tools/ToolConfirmationCard";

/** Pending tool confirmations surfaced inline above the composer, so you can act where you are. */
export function PendingActions() {
  const { data } = usePendingTools();
  if (!data || data.length === 0) return null;
  return (
    <div className="mb-2 flex flex-col gap-2">
      {data.map((p) => (
        <ToolConfirmationCard key={p.request_id} pending={p} />
      ))}
    </div>
  );
}
