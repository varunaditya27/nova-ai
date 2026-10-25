"use client";

import { Page } from "@/components/ui/Page";
import { Meter } from "@/components/ui/Bits";
import { Skeleton, Trouble } from "@/components/ui/States";
import { useRelationship, useSessions } from "@/lib/hooks/useNovaState";
import { STAGES, stageById, toNextStage } from "@/lib/stages";
import { closeness, spectrums } from "@/lib/style";
import { cn } from "@/lib/cn";

function Track({ at, left, right, label }: { at: number; left: string; right: string; label: string }) {
  return (
    <div role="img" aria-label={`${label}: ${Math.round(at * 100)} percent of the way from ${left} to ${right}`}>
      <div className="relative h-3 rounded-full bg-sunk">
        <span className="absolute top-1/2 size-6 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent" style={{ left: `${Math.round(at * 100)}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-[length:var(--text-small)] text-ink-soft">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  );
}

/** How we talk: how well Nova knows you, and the conversational style it has learned from you. */
export default function Us() {
  const rel = useRelationship();
  const sessions = useSessions();

  if (rel.isLoading) return <Page title="How we talk"><Skeleton lines={5} /></Page>;
  if (rel.isError || !rel.data) {
    return (
      <Page title="How we talk">
        <Trouble what="This page couldn’t be put together just now." onRetry={() => rel.refetch()} />
      </Page>
    );
  }
  const r = rel.data;
  const stage = stageById(r.stage);
  const idx = STAGES.findIndex((s) => s.id === stage.id);
  const next = toNextStage(r.stage, r.total_sessions);
  const convos = sessions.data ?? [];
  const longest = Math.max(1, ...convos.map((c) => c.turn_count));

  return (
    <Page
      title="How we talk"
      intro="How freely Nova speaks depends on how long you’ve known each other. Here is where you are, and the style Nova has learned from you."
    >
      <section aria-labelledby="stage" className="mb-20">
        <h2 id="stage" className="sr-only">Where we are</h2>
        <ol className="grid gap-3 sm:grid-cols-5">
          {STAGES.map((s, i) => (
            <li
              key={s.id}
              aria-current={i === idx ? "step" : undefined}
              className={cn(
                "rounded-2xl px-4 py-4",
                i === idx ? "bg-accent text-accent-ink" : i < idx ? "bg-raised" : "bg-sunk text-ink-soft"
              )}
            >
              <p className="font-display text-[length:var(--text-read)]">{s.name}</p>
              {i === idx && <p className="text-[length:var(--text-small)]">Where we are</p>}
            </li>
          ))}
        </ol>
        <p className="read mt-8 max-w-3xl">{stage.meaning}</p>
        <p className="mt-3 max-w-3xl text-ink-soft">
          {r.total_sessions} {r.total_sessions === 1 ? "conversation" : "conversations"} and {r.total_messages_exchanged} messages so far.
          {next ? ` About ${next.remaining} more ${next.remaining === 1 ? "conversation" : "conversations"} until “${next.next.name.toLowerCase()}”.` : ""}
        </p>
      </section>

      <div className="grid gap-16 lg:grid-cols-2">
        <section aria-labelledby="bond">
          <h2 id="bond" className="mb-6 text-[length:var(--text-title)]">How close it feels</h2>
          <div className="flex flex-col gap-8">
            <div>
              <p className="mb-2 flex justify-between">
                <span>Closeness</span>
                <span className="text-ink-soft">{closeness(r.tie_strength)}</span>
              </p>
              <Meter value={r.tie_strength} label="Closeness" />
              <p className="mt-2 text-[length:var(--text-small)] text-ink-soft">Grows with every conversation, faster when you share something personal.</p>
            </div>
            <div>
              <p className="mb-2 flex justify-between">
                <span>Trust</span>
                <span className="text-ink-soft">{closeness(r.trust_score)}</span>
              </p>
              <Meter value={r.trust_score} label="Trust" />
              <p className="mt-2 text-[length:var(--text-small)] text-ink-soft">Builds as you open up and Nova proves it listens.</p>
            </div>
          </div>
        </section>

        <section aria-labelledby="style">
          <h2 id="style" className="mb-2 text-[length:var(--text-title)]">How you like to talk</h2>
          <p className="mb-7 text-ink-soft">You never set these. Nova learns them from how you write, and adjusts to match.</p>
          <ul className="flex flex-col gap-8">
            {spectrums(r).map((s) => (
              <li key={s.key}>
                <Track at={s.at} left={s.left} right={s.right} label={s.sentence} />
                <p className="mt-2">{s.sentence}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {convos.length > 0 && (
        <section aria-labelledby="convos" className="mt-20">
          <h2 id="convos" className="mb-3 text-[length:var(--text-title)]">Our conversations</h2>
          <p className="mb-6 text-ink-soft">
            {convos.length} {convos.length === 1 ? "conversation" : "conversations"} so far. Each bar is one — the taller, the more you said back and forth.
          </p>
          <div role="img" aria-label={`${convos.length} conversations; the longest had ${longest} messages`} className="flex h-32 items-end gap-1.5">
            {convos.map((c) => (
              <span key={c.session_key} className="w-3 rounded-t-full bg-accent" style={{ height: `${Math.max(8, (c.turn_count / longest) * 100)}%` }} />
            ))}
          </div>
        </section>
      )}
    </Page>
  );
}
