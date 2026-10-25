"use client";

import { PendingCard } from "@/components/errands/PendingCard";
import { Page } from "@/components/ui/Page";
import { Button } from "@/components/ui/Button";
import { Empty, Skeleton, Trouble } from "@/components/ui/States";
import {
  useToolActions,
  usePendingTools,
  useToolHistory,
} from "@/lib/hooks/useTools";
import { useToast } from "@/lib/hooks/useToast";
import { operationPhrase, outcomeWords, toolName } from "@/lib/errands";

const EXAMPLES = [
  "“Remind me to call the bank tomorrow at 5.”",
  "“Put the dentist on my calendar for Friday.”",
  "“Search for the best way to learn graph algorithms.”",
  "“Take a note: ask Prof. Rao about the project.”",
];

/** Errands: things Nova can do for you. It always asks first, and most can be undone. */
export default function Errands() {
  const pending = usePendingTools();
  const history = useToolHistory();
  const { undo } = useToolActions();
  const { toast } = useToast();
  const waiting = pending.data ?? [];
  const done = [...(history.data ?? [])].reverse();

  return (
    <Page
      title="Errands"
      intro="Things Nova can do for you. It always asks before changing anything, and most things can be undone."
    >
      <section aria-labelledby="waiting" className="mb-16">
        <h2
          id="waiting"
          className="rule-top pt-4 mb-5 text-[length:var(--text-read)]"
        >
          Waiting for your OK
        </h2>
        {pending.isLoading ? (
          <Skeleton lines={2} />
        ) : pending.isError ? (
          <Trouble
            what="Nova’s waiting list couldn’t be loaded just now."
            onRetry={() => pending.refetch()}
          />
        ) : waiting.length === 0 ? (
          <div className="max-w-2xl">
            <p className="read mb-4 text-ink-soft">
              Nothing is waiting. You could try asking Nova something like:
            </p>
            <ul className="flex flex-col gap-2">
              {EXAMPLES.map((e) => (
                <li key={e} className="read">
                  {e}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <ul className="flex max-w-2xl flex-col gap-4">
            {waiting.map((e) => (
              <li key={e.request_id}>
                <PendingCard item={e} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="done">
        <h2
          id="done"
          className="rule-top pt-4 mb-5 text-[length:var(--text-read)]"
        >
          What Nova has done for you
        </h2>
        {history.isLoading ? (
          <Skeleton lines={3} />
        ) : history.isError ? (
          <Trouble
            what="The list of past errands couldn’t be loaded just now."
            onRetry={() => history.refetch()}
          />
        ) : done.length === 0 ? (
          <Empty title="No errands yet.">
            Once Nova does something for you, it’s listed here — so you always
            know what it has touched.
          </Empty>
        ) : (
          <ul className="flex max-w-3xl flex-col gap-7">
            {done.map((a) => {
              const worked = a.outcome === "success" || a.outcome === "ok";
              return (
                <li key={a.action_id} className="rule-top grid gap-1 pt-5">
                  <p className="text-[length:var(--text-small)] text-ink-soft">
                    {toolName(a.tool_name)} · Nova helped you{" "}
                    {operationPhrase(a.operation)}
                  </p>
                  <p className="read">
                    {a.result_summary || "No details were kept."}
                  </p>
                  <div className="flex items-center gap-4">
                    <span className="text-[length:var(--text-small)]">
                      {outcomeWords(a.outcome, a.undone)}
                    </span>
                    {worked && !a.undone && (
                      <Button
                        variant="text"
                        className="min-h-9"
                        disabled={undo.isPending}
                        onClick={() =>
                          undo.mutate(a.action_id, {
                            onSuccess: (r) =>
                              toast(
                                r.undone
                                  ? "Undone"
                                  : "That one can’t be undone",
                                r.undone ? undefined : "It stays as it is.",
                              ),
                            onError: () =>
                              toast(
                                "Couldn’t undo that just now",
                                "Please try again.",
                              ),
                          })
                        }
                      >
                        Undo
                      </Button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </Page>
  );
}
