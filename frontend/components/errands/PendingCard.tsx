"use client";

import { Button } from "@/components/ui/Button";
import { useToolActions } from "@/lib/hooks/useTools";
import { useToast } from "@/lib/hooks/useToast";
import { toolName } from "@/lib/errands";
import type { ToolConfirmation } from "@/lib/api/types";

/**
 * Nova asking before it acts. Says what it wants to do, whether it can be taken back, and offers a
 * plain yes or no. Nothing happens until you answer.
 */
export function PendingCard({ item }: { item: ToolConfirmation }) {
  const { confirm, deny } = useToolActions();
  const { toast } = useToast();
  const busy = confirm.isPending || deny.isPending;

  return (
    <div className="tone-sunk flex flex-col gap-4 px-6 py-5">
      <div>
        <p className="text-[length:var(--text-small)] text-ink-soft">
          {toolName(item.tool_name)} · I’d like to
        </p>
        <p className="read mt-1">{item.action_description}</p>
      </div>
      <p className="text-[length:var(--text-small)] text-ink-soft">
        {item.reversible
          ? "You can undo this afterwards."
          : "This can’t be undone once it’s done."}
      </p>
      <div className="flex flex-wrap gap-3">
        <Button
          disabled={busy}
          onClick={() =>
            confirm.mutate(item.request_id, {
              onSuccess: (r) =>
                toast(
                  r.ok ? "Done." : "That didn’t work",
                  r.ok
                    ? r.result_summary
                    : (r.error_message ?? r.result_summary),
                ),
              onError: () =>
                toast(
                  "I couldn’t do that",
                  "Nothing was changed. You can try again.",
                ),
            })
          }
        >
          Go ahead
        </Button>
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() =>
            deny.mutate(item.request_id, {
              onSuccess: () => toast("Okay, left alone.", "I won’t do that."),
            })
          }
        >
          Not now
        </Button>
      </div>
    </div>
  );
}
