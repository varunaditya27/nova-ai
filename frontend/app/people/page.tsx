"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Page } from "@/components/ui/Page";
import { Avatar } from "@/components/ui/Bits";
import { Empty, Skeleton, Trouble } from "@/components/ui/States";
import { usePeople } from "@/lib/hooks/usePeople";
import { feeling, relationshipLabel } from "@/lib/people";
import { relativeTime } from "@/lib/time";

/** The people in your life, as Nova has come to know them from what you've said. */
export default function People() {
  const q = usePeople();
  const people = [...(q.data ?? [])].sort(
    (a, b) => b.mention_count - a.mention_count,
  );
  return (
    <Page
      title="People"
      intro="Nova learns who matters to you from the way you talk about them — never from your contacts or messages with anyone else."
    >
      {q.isLoading ? (
        <Skeleton lines={4} />
      ) : q.isError ? (
        <Trouble
          what="Your people couldn’t be loaded just now."
          onRetry={() => q.refetch()}
        />
      ) : people.length === 0 ? (
        <Empty title="Nova hasn’t heard about anyone yet.">
          Mention your sister, a friend, a professor in passing — “Meera is
          visiting next week” is enough. Nova remembers them and how things are
          going between you.
        </Empty>
      ) : (
        <ul className="flex flex-col">
          {people.map((p) => (
            <li key={p.person_id}>
              <Link
                href={`/people/${p.person_id}`}
                className="group grid grid-cols-[auto_1fr_auto] items-center gap-5 cut px-4 py-5 transition-colors hover:bg-surface"
              >
                <Avatar name={p.display_name} size={60} />
                <span className="min-w-0">
                  <span className="block font-display text-[length:var(--text-title)] leading-tight">
                    {p.display_name}
                  </span>
                  <span className="block text-ink-soft">
                    {relationshipLabel(p.relationship_type)} · mentioned{" "}
                    {p.mention_count} {p.mention_count === 1 ? "time" : "times"}
                    {p.last_mentioned
                      ? `, last ${relativeTime(p.last_mentioned)}`
                      : ""}
                  </span>
                  <span className="mt-1 block">{feeling(p)}</span>
                  {(p.is_support_source || p.active_conflict) && (
                    <span className="mt-1 block text-[length:var(--text-small)] text-accent">
                      {p.is_support_source ? "Someone who supports you. " : ""}
                      {p.active_conflict
                        ? "There’s something unresolved between you."
                        : ""}
                    </span>
                  )}
                </span>
                <ArrowRight
                  aria-hidden
                  className="text-ink-soft transition-transform group-hover:translate-x-1"
                />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Page>
  );
}
