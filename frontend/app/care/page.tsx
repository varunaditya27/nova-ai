"use client";

import { Phone } from "lucide-react";
import { Page } from "@/components/ui/Page";
import { Skeleton, Trouble } from "@/components/ui/States";
import { useSafetyEvents } from "@/lib/hooks/useWellbeing";
import { HELPLINES, describeCheckIn, worthShowing } from "@/lib/care";
import { humanDay } from "@/lib/time";

/** Care: Nova notices when you're having a hard time. This is where it says so, and where real people are. */
export default function Care() {
  const q = useSafetyEvents();
  const events = worthShowing(q.data ?? []);

  return (
    <Page
      title="Care"
      intro="Nova notices when you seem to be having a hard time. This page shows when it did, and who you can call. Only you can see it."
    >
      <div className="grid gap-16 lg:grid-cols-[1fr_1.1fr]">
        <section aria-labelledby="now" className="tone self-start px-7 py-8">
          <h2
            id="now"
            className="rule-top pt-4 text-[length:var(--text-title)]"
          >
            If you need someone right now
          </h2>
          <p className="read mt-3 text-ink-soft">
            Nova is a good listener, but it isn’t a person. These are free, and
            a real human will pick up.
          </p>
          <ul className="mt-6 flex flex-col gap-5">
            {HELPLINES.map((h) => (
              <li key={h.name}>
                <a
                  href={`tel:${h.tel}`}
                  className="group inline-flex min-h-11 items-center gap-3"
                >
                  <span className="grid size-11 place-items-center bg-accent text-accent-ink">
                    <Phone size={18} aria-hidden />
                  </span>
                  <span>
                    <span className="block font-medium underline-offset-4 group-hover:underline">
                      {h.name} · {h.phone}
                    </span>
                    <span className="block text-[length:var(--text-small)] text-ink-soft">
                      {h.when}
                    </span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="times">
          <h2
            id="times"
            className="rule-top pt-4 mb-6 text-[length:var(--text-title)]"
          >
            Times Nova checked in on you
          </h2>
          {q.isLoading ? (
            <Skeleton lines={3} />
          ) : q.isError ? (
            <Trouble
              what="This list couldn’t be loaded just now."
              onRetry={() => q.refetch()}
            />
          ) : events.length === 0 ? (
            <p className="read max-w-md text-ink-soft">
              Nothing here, and that’s a good sign. If a hard moment ever comes,
              Nova will notice, respond, and record it here so you can see that
              it was there for you.
            </p>
          ) : (
            <ol className="flex flex-col gap-8">
              {events.map((e, i) => (
                <li key={`${e.detected_at}-${i}`}>
                  <p className="text-[length:var(--text-small)] text-ink-soft">
                    {humanDay(e.detected_at)}
                  </p>
                  <p className="read max-w-xl">{describeCheckIn(e.tier)}</p>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </Page>
  );
}
