"use client";

import Link from "next/link";
import { Surface } from "@/components/primitives/Surface";
import { Meter } from "@/components/primitives/Meter";
import type { PersonOut } from "@/lib/api/types";

/** A person Nova knows about — relationship type, valence, and whether there's active tension. */
export function PersonCard({ person }: { person: PersonOut }) {
  return (
    <Link href={`/people/${person.person_id}`}>
      <Surface className="p-5 transition-colors hover:bg-raised">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-display text-lg text-ink">{person.display_name}</p>
          <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
            {person.relationship_type.replace(/_/g, " ")}
          </span>
        </div>
        <Meter
          value={(person.relationship_valence + 1) / 2}
          brass={person.is_support_source}
          className="mt-3"
        />
        <div className="mt-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          <span>{person.mention_count} mention{person.mention_count === 1 ? "" : "s"}</span>
          {person.active_conflict && <span className="text-brass">active tension</span>}
        </div>
      </Surface>
    </Link>
  );
}
