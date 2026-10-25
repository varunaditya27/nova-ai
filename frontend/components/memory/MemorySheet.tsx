"use client";

import { useState } from "react";
import { Sheet } from "@/components/ui/Sheet";
import { Button } from "@/components/ui/Button";
import { Skeleton, Trouble } from "@/components/ui/States";
import { useDeleteMemory, useMemoryDetail } from "@/lib/hooks/useVault";
import { useToast } from "@/lib/hooks/useToast";
import { longDate, relativeTime } from "@/lib/time";
import type { MemoryDeletion } from "@/lib/api/types";

/** A short, readable number for a long signed receipt: first and last characters. */
export function receiptNumber(certificate: string): string {
  return certificate.length <= 16 ? certificate : `${certificate.slice(0, 8)}…${certificate.slice(-6)}`.toUpperCase();
}

/** What Nova stores about how much a memory matters, in a word rather than a decimal. */
function weight(importance: number): string {
  if (importance >= 0.75) return "Nova treats this as very important";
  if (importance >= 0.45) return "Nova treats this as fairly important";
  return "Nova treats this as a passing detail";
}

/** One memory in full, and the only place that can make Nova forget it — in two deliberate steps. */
export function MemorySheet({ id, onClose }: { id: string | null; onClose: () => void }) {
  const q = useMemoryDetail(id);
  const forget = useDeleteMemory();
  const { toast } = useToast();
  const [confirming, setConfirming] = useState(false);
  const [receipt, setReceipt] = useState<MemoryDeletion | null>(null);

  const close = () => {
    setConfirming(false);
    setReceipt(null);
    onClose();
  };

  return (
    <Sheet open={Boolean(id)} onClose={close} title={receipt ? "Forgotten" : "A memory"}>
      {receipt ? (
        <div className="flex flex-col gap-5">
          <p className="read">
            Nova can no longer recall this, and its words have been erased from memory. The signed receipt below proves it happened and can’t be forged.
          </p>
          {receipt.cascade && (
            <p className="text-ink-soft">
              <span className="text-ink">Also tidied up: </span>
              {receipt.cascade}
            </p>
          )}
          <p className="tone-sunk px-5 py-4">
            <span className="block text-[length:var(--text-small)] text-ink-soft">Receipt number</span>
            <span className="text-[length:var(--text-read)]" aria-label="Receipt number">
              {receiptNumber(receipt.certificate)}
            </span>
          </p>
          <div className="flex gap-3">
            <Button variant="quiet" onClick={() => navigator.clipboard?.writeText(receipt.certificate).then(() => toast("Full receipt copied", "Keep it somewhere safe — it proves this memory was erased."))}>
              Copy full receipt
            </Button>
            <Button onClick={close}>Done</Button>
          </div>
        </div>
      ) : q.isLoading ? (
        <Skeleton lines={4} />
      ) : q.isError || !q.data ? (
        <Trouble what="That memory couldn’t be opened. It may already have been forgotten." onRetry={() => q.refetch()} />
      ) : (
        <div className="flex flex-col gap-6">
          <p className="read whitespace-pre-wrap">{q.data.summary}</p>
          <p className="text-ink-soft">
            From {longDate(q.data.created_at)} ({relativeTime(q.data.created_at)}). {weight(q.data.importance)}.
          </p>
          {q.data.topic_tags.length > 0 && (
            <p className="text-ink-soft">
              About: <span className="text-ink">{q.data.topic_tags.join(", ")}</span>
            </p>
          )}

          {!confirming ? (
            <div className="pt-4">
              <Button variant="quiet" onClick={() => setConfirming(true)}>
                Ask Nova to forget this
              </Button>
            </div>
          ) : (
            <div role="alertdialog" aria-label="Confirm forgetting" className="tone-sunk flex flex-col gap-4 px-6 py-6">
              <h3 className="text-[length:var(--text-read)]">Forget this for good?</h3>
              <p>
                Nova will erase what it remembers about this and will never bring it up again. You’ll get a signed receipt.
              </p>
              <p className="text-ink-soft">
                The original messages stay in your conversation history, and this can’t be undone.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button
                  variant="danger"
                  disabled={forget.isPending}
                  onClick={() =>
                    forget.mutate(q.data.memory_id, {
                      onSuccess: (r) => setReceipt(r),
                      onError: () => toast("Couldn’t forget that just now", "Nothing was changed. Please try again."),
                    })
                  }
                >
                  {forget.isPending ? "Forgetting…" : "Yes, forget it"}
                </Button>
                <Button variant="quiet" onClick={() => setConfirming(false)}>
                  Keep it
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </Sheet>
  );
}
