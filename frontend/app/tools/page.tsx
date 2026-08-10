"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { ToolConfirmationCard } from "@/components/tools/ToolConfirmationCard";
import { usePendingTools, useToolActions, useToolHistory } from "@/lib/hooks/useTools";
import { useToast } from "@/lib/hooks/useToast";

/** Actions — what Nova can do in the world: awaiting your say-so, and what it has already done. */
export default function Tools() {
  const { data: pending } = usePendingTools();
  const { data: history } = useToolHistory();
  const { undo } = useToolActions();
  const { toast } = useToast();

  const onUndo = (actionId: string) =>
    undo.mutate(actionId, {
      onSuccess: (r) => toast(r.undone ? "Undone." : "Can't be undone."),
    });

  return (
    <PageShell
      title="Actions"
      description="Things Nova can do in the world — waiting on your say-so, and a record of what it's done."
    >
      {pending && pending.length > 0 && (
        <section className="mb-8">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-brass">
            awaiting you · {pending.length}
          </p>
          <div className="flex flex-col gap-3">
            {pending.map((p) => (
              <ToolConfirmationCard key={p.request_id} pending={p} />
            ))}
          </div>
        </section>
      )}

      <section>
        <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
          history · {history?.length ?? 0}
        </p>
        {history && history.length === 0 && <p className="text-ink-soft">Nothing done yet.</p>}
        <div className="flex flex-col gap-2">
          {history?.map((a) => (
            <Surface key={a.action_id} className="p-4">
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[15px] leading-relaxed text-ink">{a.result_summary}</p>
                <span
                  className="shrink-0 font-mono text-[10px] uppercase tracking-widest"
                  style={{ color: a.outcome === "success" ? "var(--ink-faint)" : "var(--brass)" }}
                >
                  {a.outcome}
                </span>
              </div>
              <div className="mt-0.5 flex items-baseline justify-between gap-3">
                <p className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                  {a.tool_name.replace(/_/g, " ")} · {a.operation}
                  {a.undone ? " · undone" : ""}
                </p>
                {a.outcome === "success" && !a.undone && (
                  <button
                    onClick={() => onUndo(a.action_id)}
                    disabled={undo.isPending}
                    className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-ink-faint underline-offset-2 transition-colors hover:text-brass hover:underline disabled:opacity-50"
                  >
                    undo
                  </button>
                )}
              </div>
            </Surface>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
