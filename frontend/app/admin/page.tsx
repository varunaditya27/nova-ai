"use client";

import { useState } from "react";
import { Loader2, Play } from "lucide-react";
import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { runJob } from "@/lib/api/client";
import type { JobRunOut } from "@/lib/api/types";

const JOBS: { name: string; label: string; description: string }[] = [
  { name: "integrity_check", label: "Integrity check", description: "Verify both tamper-evident hash chains." },
  { name: "memory_consolidation", label: "Memory consolidation", description: "Decay sweep, then persist — prune and strengthen memory." },
  { name: "proactive_check", label: "Proactive check", description: "Recompute and expire the outreach queue." },
  { name: "longitudinal_summary", label: "Longitudinal summary", description: "Generate this week's chapter." },
  { name: "pattern_detection", label: "Pattern detection", description: "Surface recurring patterns across the history." },
];

type Outcome = { ok: true; data: JobRunOut } | { ok: false; error: string };

/** Ops — run any background job on demand and read its summary. Single-user, no auth. */
export default function Admin() {
  const [running, setRunning] = useState<string | null>(null);
  const [outcomes, setOutcomes] = useState<Record<string, Outcome>>({});

  const run = async (name: string) => {
    setRunning(name);
    try {
      const data = await runJob(name);
      setOutcomes((p) => ({ ...p, [name]: { ok: true, data } }));
    } catch (e) {
      setOutcomes((p) => ({ ...p, [name]: { ok: false, error: (e as Error).message } }));
    } finally {
      setRunning(null);
    }
  };

  return (
    <PageShell title="Machine room" description="Run Nova's background jobs by hand and read what they did.">
      <div className="flex flex-col gap-3">
        {JOBS.map((job) => {
          const outcome = outcomes[job.name];
          const isRunning = running === job.name;
          return (
            <Surface key={job.name} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-display text-lg text-ink">{job.label}</p>
                  <p className="mt-0.5 text-sm text-ink-soft">{job.description}</p>
                </div>
                <button
                  onClick={() => run(job.name)}
                  disabled={isRunning}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-hairline bg-raised px-3 py-1.5 text-sm text-ink transition-colors hover:bg-paper disabled:opacity-60"
                >
                  {isRunning ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                  Run
                </button>
              </div>
              {outcome && (
                <pre className="mt-3 max-h-52 overflow-auto rounded-md border border-hairline bg-paper px-3 py-2 font-mono text-[11px] leading-relaxed text-ink-soft">
                  {outcome.ok
                    ? JSON.stringify(outcome.data.result, null, 2)
                    : `error: ${outcome.error}`}
                </pre>
              )}
            </Surface>
          );
        })}
      </div>
    </PageShell>
  );
}
