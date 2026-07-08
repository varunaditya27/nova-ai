"use client";

import { Check, X } from "lucide-react";
import { Surface } from "@/components/primitives/Surface";
import { useToolActions } from "@/lib/hooks/useTools";
import { useToast } from "@/lib/hooks/useToast";
import type { ToolConfirmation } from "@/lib/api/types";

/** A pending SOFT/HARD action with Confirm (executes) / Deny. Irreversible actions read brass. */
export function ToolConfirmationCard({ pending }: { pending: ToolConfirmation }) {
  const { confirm, deny } = useToolActions();
  const { toast } = useToast();
  const busy = confirm.isPending || deny.isPending;

  const onConfirm = () =>
    confirm.mutate(pending.request_id, {
      onSuccess: (r) =>
        toast(
          r.ok ? "Done." : "Couldn't complete that.",
          r.result_summary || r.error_message || undefined
        ),
    });

  return (
    <Surface className="p-4" raised>
      <div className="mb-1.5 flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          {pending.tool_name.replace(/_/g, " ")}
        </span>
        <span
          className="rounded-sm border border-hairline px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest"
          style={{ color: pending.reversible ? "var(--ink-faint)" : "var(--brass)" }}
        >
          {pending.tier}
          {pending.reversible ? "" : " · irreversible"}
        </span>
      </div>
      <p className="text-[15px] leading-relaxed text-ink">{pending.action_description}</p>
      <div className="mt-3 flex gap-2">
        <button
          onClick={onConfirm}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-md border border-brass/40 px-3 py-1.5 text-sm text-brass transition-colors hover:bg-brass/5 disabled:opacity-50"
        >
          <Check size={14} /> Confirm
        </button>
        <button
          onClick={() => deny.mutate(pending.request_id)}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-md border border-hairline px-3 py-1.5 text-sm text-ink-soft transition-colors hover:bg-raised disabled:opacity-50"
        >
          <X size={14} /> Deny
        </button>
      </div>
    </Surface>
  );
}
