"use client";

import { useState } from "react";
import { NOTES } from "@/lib/voice";
import { Page } from "@/components/ui/Page";
import { Button } from "@/components/ui/Button";
import { runJob } from "@/lib/api/client";
import { CHORES, describeResult } from "@/lib/upkeep";

type Outcome =
  | { state: "running" }
  | { state: "done"; rows: { label: string; value: string }[] }
  | { state: "failed" };

/** Upkeep: Nova's housekeeping. It runs itself on a schedule; here you can run any of it by hand. */
export default function Upkeep() {
  const [outcomes, setOutcomes] = useState<Record<string, Outcome>>({});

  const run = async (name: string) => {
    setOutcomes((o) => ({ ...o, [name]: { state: "running" } }));
    try {
      const r = await runJob(name);
      setOutcomes((o) => ({
        ...o,
        [name]: { state: "done", rows: describeResult(r.result) },
      }));
    } catch {
      setOutcomes((o) => ({ ...o, [name]: { state: "failed" } }));
    }
  };

  return (
    <Page
      title="Upkeep"
      note={NOTES.upkeep}
      intro="I tidy my memory and think things over on a schedule. You can make me do any of it now."
    >
      <ul className="flex max-w-3xl flex-col gap-10">
        {CHORES.map((c) => {
          const out = outcomes[c.name];
          return (
            <li
              key={c.name}
              className="rule-top grid gap-3 pt-5 sm:grid-cols-[1fr_auto] sm:items-start sm:gap-8"
            >
              <div>
                <h2 className="text-[length:var(--text-read)]">{c.title}</h2>
                <p className="mt-1 text-ink-soft">{c.what}</p>
                <p className="mt-1 text-[length:var(--text-small)] text-mute">
                  Runs by itself: {c.when.toLowerCase()}
                </p>
                <div aria-live="polite">
                  {out?.state === "done" && (
                    <dl className="tone mt-4 grid max-w-md gap-1.5 px-5 py-4">
                      {out.rows.length === 0 && (
                        <p>Done. Nothing to report, which is the best kind.</p>
                      )}
                      {out.rows.map((r) => (
                        <div
                          key={r.label}
                          className="flex justify-between gap-6"
                        >
                          <dt className="text-ink-soft">{r.label}</dt>
                          <dd>{r.value}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {out?.state === "failed" && (
                    <p className="mt-3 text-danger">
                      That didn’t run. Nothing was changed, and you can try again.
                    </p>
                  )}
                </div>
              </div>
              <Button
                variant="quiet"
                onClick={() => run(c.name)}
                disabled={out?.state === "running"}
              >
                {out?.state === "running" ? "On it…" : "Run it now"}
              </Button>
            </li>
          );
        })}
      </ul>
    </Page>
  );
}
