"use client";

import { useRef, type ReactNode } from "react";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";
import { CareSpecimen, ErrandSpecimen, GoalSpecimen, MemorySpecimen, PeopleSpecimen, StorySpecimen } from "./Specimens";

const ROWS: { title: string; body: string; specimen: ReactNode }[] = [
  {
    title: "It remembers what matters",
    body: "Not every word. The news, the worries and the plans worth keeping. You can read all of it on the Memory page, and ask Nova to forget any of it.",
    specimen: <MemorySpecimen />,
  },
  {
    title: "It notices how you’re doing",
    body: "How you’re writing, when you’ve gone quiet, when something sounds heavy. If you’re struggling it checks in, and tells you who you can call.",
    specimen: <CareSpecimen />,
  },
  {
    title: "It helps you follow through",
    body: "Tell it a goal and it breaks it into steps, and keeps count of the habits that get you there. It remembers the deadline, so you don’t have to.",
    specimen: <GoalSpecimen />,
  },
  {
    title: "It keeps your story",
    body: "Each week becomes a short chapter, written from what you shared. Months later you can read how things actually went, not just how you remember them.",
    specimen: <StorySpecimen />,
  },
  {
    title: "It knows the people in your life",
    body: "Names, how they’re connected to you, what’s happening with them. Nova asks after your sister because it knows she exists.",
    specimen: <PeopleSpecimen />,
  },
  {
    title: "It does errands, with your say-so",
    body: "Reminders, calendar events, notes. Nova always asks first, tells you whether it can be undone, and keeps a record of what it did.",
    specimen: <ErrandSpecimen />,
  },
];

/**
 * Six panels in a row. On a wide screen the page stops and the row slides past as you scroll, like a
 * reel; on a phone, or with motion turned down, they are simply stacked.
 */
export function Capabilities() {
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(`${MOTION_OK} and (min-width: 1024px)`, () => {
        const el = root.current!;
        el.dataset.pinned = "true";
        const track = el.querySelector<HTMLElement>("[data-reel]")!;
        const dist = () => track.scrollWidth - el.clientWidth;
        gsap
          .timeline({ defaults: { ease: "none" }, scrollTrigger: { trigger: el, start: "top top", end: () => `+=${dist()}`, pin: true, anticipatePin: 1, scrub: 0.8, invalidateOnRefresh: true } })
          .to(track, { x: () => -dist() }, 0)
          .fromTo("[data-reel-progress]", { scaleX: 0 }, { scaleX: 1 }, 0);
        return () => delete el.dataset.pinned;
      });
    },
    { scope: root }
  );

  return (
    <section id="does" ref={root} aria-label="What Nova does" className="group overflow-hidden bg-sunk py-20 sm:py-28 lg:flex lg:min-h-dvh lg:flex-col lg:justify-center lg:py-12">
      <div className="mx-auto mb-12 w-full max-w-6xl px-5 sm:px-8 lg:px-12">
        <h2 className="text-[length:var(--text-title)]">What it does for you.</h2>
        <p className="read mt-4 max-w-2xl text-ink-soft">Each picture is an example of a real screen, playing out.</p>
      </div>
      <ul data-reel className="flex flex-col gap-20 px-5 sm:px-8 lg:w-max lg:flex-row lg:gap-10 lg:px-12 lg:group-data-[pinned=true]:gap-8">
        {ROWS.map((r, i) => (
          <li key={r.title} className="lg:w-[min(64rem,76vw)] lg:shrink-0">
            <div className="grid items-center gap-8 lg:grid-cols-2 lg:gap-14">
              <div>
                <span aria-hidden className="outline-text mb-3 block font-display text-[length:var(--text-display)] leading-none text-ink-soft">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="text-[length:var(--text-title)]">{r.title}</h3>
                <p className="read mt-4 text-ink-soft">{r.body}</p>
              </div>
              <div>{r.specimen}</div>
            </div>
          </li>
        ))}
      </ul>
      <div aria-hidden className="mx-auto mt-12 hidden h-[3px] w-full max-w-6xl bg-ground lg:group-data-[pinned=true]:block">
        <div data-reel-progress className="h-full origin-left bg-accent" />
      </div>
    </section>
  );
}
