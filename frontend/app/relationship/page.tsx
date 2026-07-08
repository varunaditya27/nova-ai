"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { Meter } from "@/components/primitives/Meter";
import { useRelationship } from "@/lib/hooks/useNovaState";

const STAGES = ["new", "acquaintance", "developing", "established", "close"];

/** You & Nova — stage progression and the communication style Nova has quietly learned. */
export default function Relationship() {
  const { data, isLoading } = useRelationship();
  const stageIndex = data ? STAGES.indexOf(data.stage) : -1;

  return (
    <PageShell
      title="You & Nova"
      description="Where things stand — and what Nova has learned about how you like to talk."
    >
      {isLoading && <div className="h-40 rounded-md bg-hairline/30" />}
      {data && (
        <div className="flex flex-col gap-9">
          <div>
            <p className="font-display text-2xl capitalize text-ink">{data.stage}</p>
            <p className="mt-1 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
              {data.total_sessions} sessions · {data.total_messages_exchanged} messages
            </p>
            <div className="mt-4 flex gap-1">
              {STAGES.map((s, i) => (
                <span
                  key={s}
                  title={s}
                  className="h-1 flex-1 rounded-full"
                  style={{ background: i <= stageIndex ? "var(--ink-soft)" : "var(--hairline)" }}
                />
              ))}
            </div>
          </div>

          <div>
            <p className="mb-5 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
              what Nova has learned
            </p>
            <div className="flex max-w-md flex-col gap-6">
              <Meter value={data.formality_preference} leftLabel="casual" rightLabel="formal" />
              <Meter value={data.response_length_preference} leftLabel="terse" rightLabel="verbose" />
              <Meter
                value={data.question_tolerance}
                leftLabel="few questions"
                rightLabel="welcomes questions"
              />
              <Meter
                value={data.unsolicited_advice_tolerance}
                leftLabel="no advice"
                rightLabel="open to advice"
              />
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
