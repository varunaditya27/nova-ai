"use client";

import { Button } from "@/components/ui/Button";
import { Ember } from "@/components/ui/Ember";
import { Section, Reveal } from "./Section";
import { SECTIONS } from "./Header";
import { useBegin } from "./useBegin";

export function Closing() {
  const begin = useBegin();
  return (
    <>
      <Section label="Begin">
        <Reveal className="flex flex-col items-start gap-8 py-8">
          <h2 className="text-[length:var(--text-display)]">Say the first thing.</h2>
          <p className="read max-w-xl text-ink-soft">There’s nothing to sign up for. Start whenever you like.</p>
          <Button onClick={begin}>Begin the conversation</Button>
        </Reveal>
      </Section>
      <footer className="px-5 pb-12 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6">
          <p className="flex items-center gap-2.5 font-display text-2xl">
            <Ember size={24} className="text-accent" /> Nova
          </p>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-8 gap-y-2">
            {SECTIONS.map((s) => (
              <a key={s.href} href={s.href} className="inline-flex min-h-11 items-center text-ink-soft underline-offset-4 hover:text-ink hover:underline">
                {s.label}
              </a>
            ))}
          </nav>
        </div>
      </footer>
    </>
  );
}
