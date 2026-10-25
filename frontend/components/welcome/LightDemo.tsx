"use client";

import { useState } from "react";
import { Ember } from "@/components/ui/Ember";
import { useLight, type Light } from "@/components/ThemeProvider";
import { cn } from "@/lib/cn";
import { Section, Reveal, SectionHead } from "./Section";

const LIGHTS: {
  value: Light;
  label: string;
  hours: string;
  greeting: string;
  line: string;
}[] = [
  {
    value: "dawn",
    label: "Dawn",
    hours: "5 to 8 am",
    greeting: "Early start.",
    line: "Soft and pink, for the quiet hour before the day begins.",
  },
  {
    value: "day",
    label: "Day",
    hours: "8 am to 5 pm",
    greeting: "Good afternoon.",
    line: "Bright and clear, for when you’re busy and want to see everything.",
  },
  {
    value: "dusk",
    label: "Dusk",
    hours: "5 to 8 pm",
    greeting: "Winding down?",
    line: "Calmer and deeper, as the day settles.",
  },
  {
    value: "night",
    label: "Night",
    hours: "8 pm to 5 am",
    greeting: "Still up?",
    line: "Dark and easy on the eyes, for late conversations.",
  },
];

/** The room changes with the hour. Pick a time of day and the sample re-lights itself. */
export function LightDemo() {
  const { light: now } = useLight();
  const [picked, setPicked] = useState<Light | null>(null);
  const active = picked ?? now;
  const current = LIGHTS.find((l) => l.value === active) ?? LIGHTS[1];

  return (
    <Section id="light" label="The room matches your day">
      <SectionHead n="06" name="The light" />
      <div className="grid items-center gap-12 lg:grid-cols-12 lg:gap-16">
        <Reveal className="lg:col-span-5">
          <h2 className="text-[length:var(--text-title)]">
            The room matches your day.
          </h2>
          <p className="read mt-5 text-ink-soft">
            Nova’s colours follow the hour where you are. You can also keep it
            light or dark all the time, from the sidebar once you’re inside.
          </p>
          <div
            role="radiogroup"
            aria-label="Time of day"
            className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2"
          >
            {LIGHTS.map((l) => (
              <button
                key={l.value}
                role="radio"
                aria-checked={active === l.value}
                onClick={() => setPicked(l.value)}
                className={cn(
                  "flex min-h-14 flex-col items-start justify-center cut px-5 text-left transition-colors duration-200",
                  active === l.value
                    ? "bg-ink text-ground"
                    : "bg-sunk hover:bg-raised",
                )}
              >
                <span className="font-medium">{l.label}</span>
                <span
                  className={cn(
                    "text-[length:var(--text-small)]",
                    active !== l.value && "text-ink-soft",
                  )}
                >
                  {l.hours}
                </span>
              </button>
            ))}
          </div>
        </Reveal>

        <Reveal className="lg:col-span-7">
          <div
            data-light={active}
            className="cut bg-surface px-7 py-9 text-ink transition-colors duration-700 sm:px-10"
            aria-label={`A sample conversation in the ${current.label.toLowerCase()} light`}
            role="group"
          >
            <p className="flex items-center gap-2.5 font-display text-2xl">
              <Ember size={24} state="idle" className="text-accent" />{" "}
              {current.greeting}
            </p>
            <div className="mt-8 flex flex-col gap-5">
              <div className="ml-auto max-w-[85%] cut bg-sunk px-5 py-3">
                Can we talk about my week?
              </div>
              <p className="read max-w-[90%]">Of course. {current.line}</p>
              <div className="flex gap-3">
                <span className="inline-flex min-h-11 items-center cut-sm bg-accent px-6 font-medium text-accent-ink">
                  Go ahead
                </span>
                <span className="inline-flex min-h-11 items-center cut-sm bg-sunk px-6">
                  Not now
                </span>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
