import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Section, Reveal } from "./Section";
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

export function Capabilities() {
  return (
    <Section id="does" tone="sunk" label="What Nova does">
      <Reveal className="mb-16 max-w-3xl">
        <h2 className="text-[length:var(--text-title)]">What it does for you.</h2>
        <p className="read mt-5 max-w-2xl text-ink-soft">Pictures below are examples of the real screens.</p>
      </Reveal>
      <ul className="flex flex-col gap-20 sm:gap-24">
        {ROWS.map((r, i) => (
          <li key={r.title}>
            <Reveal className="grid items-center gap-8 lg:grid-cols-12 lg:gap-16">
              <div className={cn("lg:col-span-5", i % 2 === 1 && "lg:order-2 lg:col-start-8")}>
                <h3 className="text-[length:var(--text-title)]">{r.title}</h3>
                <p className="read mt-4 text-ink-soft">{r.body}</p>
              </div>
              <div className={cn("lg:col-span-6", i % 2 === 1 ? "lg:order-1 lg:col-start-1" : "lg:col-start-7")}>{r.specimen}</div>
            </Reveal>
          </li>
        ))}
      </ul>
    </Section>
  );
}
