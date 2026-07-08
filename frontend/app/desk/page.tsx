"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useHome } from "@/lib/hooks/useHome";
import { useOnboarding } from "@/lib/hooks/useNovaState";
import { useAcoustics } from "@/lib/hooks/useAcoustics";
import { GreetingBand } from "@/components/desk/GreetingBand";
import { CurrentChapter } from "@/components/desk/CurrentChapter";
import { HeldThought } from "@/components/desk/HeldThought";
import { Weather } from "@/components/desk/Weather";

/** Loading is a calm settle — faint hairline blocks, never a spinner. */
function DeskSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-hidden>
      <div className="h-9 w-52 rounded-md bg-hairline/60" />
      <div className="h-5 w-80 max-w-full rounded-md bg-hairline/40" />
      <div className="h-24 w-full max-w-lg rounded-md bg-hairline/30" />
    </div>
  );
}

/**
 * The Digital Desk — the logged-in landing. Greeting, current chapter, a thought Nova is holding,
 * one way forward, and the ambient weather of the relationship. Beautiful when empty.
 */
export default function Desk() {
  const { data, isLoading, isError } = useHome();
  const { data: onboarding } = useOnboarding();
  const { play } = useAcoustics();

  return (
    <main className="relative z-10 mx-auto flex min-h-dvh max-w-2xl flex-col justify-center gap-8 px-6 py-24 sm:px-10">
      {isLoading && <DeskSkeleton />}

      {isError && !data && (
        <p className="text-ink-soft">
          The desk is quiet right now — it&rsquo;ll be here when Nova is.
        </p>
      )}

      {data && (
        <>
          <GreetingBand greeting={data.greeting} />

          {onboarding?.cold_start_active && (
            <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-brass">
              Still getting to know you · session {onboarding.session_index}
            </p>
          )}

          {data.message_count === 0 ? (
            <p className="max-w-lg text-lg leading-relaxed text-ink-soft">
              This is where your life together will gather. For now it&rsquo;s a blank page &mdash;
              go say the first thing.
            </p>
          ) : (
            <CurrentChapter chapter={data.current_chapter} />
          )}

          <HeldThought thought={data.top_proactive} />

          <div className="flex flex-wrap items-center gap-5">
            <Link
              href="/chat"
              onClick={() => play("click")}
              style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
              className="group inline-flex items-center gap-2 rounded-md border border-hairline bg-surface px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-raised"
            >
              {data.message_count === 0 ? "Say the first thing" : "Continue"}
              <ArrowRight
                size={15}
                className="transition-transform duration-300 group-hover:translate-x-0.5"
              />
            </Link>
            {data.active_goals > 0 && (
              <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
                {data.active_goals} goal{data.active_goals === 1 ? "" : "s"} in motion
              </span>
            )}
          </div>

          <Weather
            weather={data.weather}
            stage={data.relationship_stage}
            lastInteraction={data.last_interaction_at}
          />
        </>
      )}
    </main>
  );
}
