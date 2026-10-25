"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Page } from "@/components/ui/Page";
import { Avatar } from "@/components/ui/Bits";
import { Skeleton, Trouble } from "@/components/ui/States";
import { usePerson } from "@/lib/hooks/usePeople";
import {
  feeling,
  howOften,
  patternSureness,
  plainEvent,
  relationshipLabel,
} from "@/lib/people";
import { humanDay } from "@/lib/time";

/** One person: how things stand, what has happened between you, and what Nova has noticed. */
export default function Person() {
  const { id } = useParams<{ id: string }>();
  const q = usePerson(id);

  if (q.isLoading)
    return (
      <Page title="…">
        <Skeleton lines={4} />
      </Page>
    );
  if (q.isError || !q.data) {
    return (
      <Page title="Person">
        <Trouble
          what="This person couldn’t be found. They may have been removed."
          onRetry={() => q.refetch()}
        />
      </Page>
    );
  }
  const p = q.data;
  const patterns = p.active_patterns.filter((x) => x.is_active);
  const events = [...p.recent_events].sort(
    (a, b) =>
      new Date(b.event_timestamp ?? 0).getTime() -
      new Date(a.event_timestamp ?? 0).getTime(),
  );

  return (
    <Page
      title={p.display_name}
      intro={[
        relationshipLabel(p.relationship_type) + ".",
        feeling(p),
        howOften(p.interaction_frequency),
      ]
        .filter(Boolean)
        .join(" ")}
      actions={
        <Link
          href="/people"
          className="inline-flex min-h-11 items-center gap-2 cut-sm bg-sunk px-5 hover:bg-raised"
        >
          <ArrowLeft size={16} aria-hidden /> All people
        </Link>
      }
    >
      <div className="mb-12 flex items-center gap-5">
        <Avatar name={p.display_name} size={72} />
        <p className="max-w-xl text-ink-soft">
          {p.is_support_source
            ? "Nova sees them as someone who supports you. "
            : ""}
          {p.active_conflict
            ? "There’s something unresolved between you two right now."
            : ""}
        </p>
      </div>

      <div className="grid gap-14 lg:grid-cols-2">
        <section aria-labelledby="events">
          <h2 id="events" className="mb-5 text-[length:var(--text-read)]">
            What’s happened
          </h2>
          {events.length === 0 ? (
            <p className="text-ink-soft">
              Nothing specific yet — just that you’ve mentioned them.
            </p>
          ) : (
            <ol className="flex flex-col gap-6">
              {events.map((e) => (
                <li key={e.event_id}>
                  <p className="text-[length:var(--text-small)] text-ink-soft">
                    {plainEvent(e.event_type)} · {humanDay(e.event_timestamp)}
                    {e.is_resolved ? " · sorted out" : ""}
                  </p>
                  <p className="read">{e.summary}</p>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section aria-labelledby="noticed">
          <h2 id="noticed" className="mb-5 text-[length:var(--text-read)]">
            What Nova has noticed
          </h2>
          {patterns.length === 0 ? (
            <p className="text-ink-soft">
              No patterns yet. Nova looks for them once there’s enough history
              to be fair.
            </p>
          ) : (
            <ul className="flex flex-col gap-6">
              {patterns.map((x) => (
                <li key={x.pattern_id}>
                  <p className="read">{x.plain_language_description}</p>
                  <p className="text-[length:var(--text-small)] text-ink-soft">
                    {patternSureness(x.pattern_confidence)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </Page>
  );
}
