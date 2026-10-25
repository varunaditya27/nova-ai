"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Mark } from "@/components/ui/Mark";
import type { Echo } from "@/lib/api/types";

/**
 * The one ambient thing allowed near a reply: what Nova drew on to write it. Collapsed to a single
 * quiet line; open it and each memory is shown in Nova's own words with when it happened.
 */
export function Echoes({ echoes }: { echoes: Echo[] }) {
  const [open, setOpen] = useState(false);
  if (echoes.length === 0) return null;
  const n = echoes.length;
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="inline-flex min-h-9 items-center gap-2 bg-sunk px-4 text-[length:var(--text-small)] text-ink-soft hover:text-ink"
      >
        <Mark size={14} />
        I remembered {n === 1 ? "something" : `${n} things`} for this
        <ChevronDown
          size={14}
          aria-hidden
          className={
            open ? "rotate-180 transition-transform" : "transition-transform"
          }
        />
      </button>
      {open && (
        <ul className="mt-3 flex flex-col gap-3">
          {echoes.map((e, i) => (
            <li key={i} className="tone px-5 py-3">
              <p className="italic">“{e.summary}”</p>
              {e.when && (
                <p className="mt-1 text-[length:var(--text-small)] text-mute">
                  {e.when}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
