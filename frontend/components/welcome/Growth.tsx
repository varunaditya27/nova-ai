"use client";

import { useState } from "react";
import { Tabs } from "@/components/ui/Tabs";
import { Section, Reveal } from "./Section";

type Stage = "first" | "weeks" | "months" | "years";

const STAGES: Record<Stage, { label: string; knows: string[]; acts: string }> = {
  first: {
    label: "First day",
    knows: ["Only what you’ve just said."],
    acts: "Nova listens more than it talks. It asks very little, doesn’t bring up the past, and won’t message you first while it learns how you like to talk.",
  },
  weeks: {
    label: "Three weeks",
    knows: ["Your name, and what you’re studying.", "The exam on Friday, and how nervous you were.", "That your sister is called Meera."],
    acts: "After about five conversations Nova opens up. It refers back to what you’ve told it, and checks in on things that matter to you.",
  },
  months: {
    label: "Six months",
    knows: ["Around twenty-five weekly chapters of your story.", "That you talk most on Sunday evenings.", "That you’re happier in the weeks you go running."],
    acts: "Nova starts to notice patterns, and mentions them gently, as something it has seen rather than a verdict.",
  },
  years: {
    label: "Two years",
    knows: ["The people who matter, and how often you speak of them.", "The moments you marked as mattering.", "Every goal you’ve set, finished or let go."],
    acts: "Nova can look back with you: on anniversaries, and at the end of a year, on how far you’ve come.",
  },
};

/** Memory is the product, and it builds slowly. The same example person, at four points in time. */
export function Growth() {
  const [stage, setStage] = useState<Stage>("weeks");
  const s = STAGES[stage];
  return (
    <Section id="how" label="How it grows">
      <Reveal className="mb-10 max-w-3xl">
        <h2 className="text-[length:var(--text-title)]">It gets to know you slowly.</h2>
        <p className="read mt-5 max-w-2xl text-ink-soft">
          Nova doesn’t pretend to know you on day one. Here is what knowing someone looks like as time passes, for an example person.
        </p>
      </Reveal>
      <Reveal>
        <Tabs
          label="A point in time"
          value={stage}
          onChange={setStage}
          items={(Object.keys(STAGES) as Stage[]).map((k) => ({ value: k, label: STAGES[k].label }))}
        />
        <div role="tabpanel" aria-label={s.label} className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="tone px-7 py-8 sm:px-9">
            <h3 className="font-display text-[length:var(--text-read)]">What Nova knows</h3>
            <ul className="read mt-5 flex flex-col gap-3">
              {s.knows.map((k) => (
                <li key={k} className="relative pl-6">
                  <span aria-hidden className="absolute left-0 top-[0.7em] size-2.5 rounded-full bg-accent" />
                  {k}
                </li>
              ))}
            </ul>
          </div>
          <div className="tone-sunk px-7 py-8 sm:px-9">
            <h3 className="font-display text-[length:var(--text-read)]">How it behaves</h3>
            <p className="read mt-5">{s.acts}</p>
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
