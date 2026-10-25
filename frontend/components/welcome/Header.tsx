"use client";

import { Ember } from "@/components/ui/Ember";
import { Button } from "@/components/ui/Button";
import { useBegin } from "./useBegin";

export const SECTIONS = [
  { href: "#how", label: "How it grows" },
  { href: "#does", label: "What it does" },
  { href: "#private", label: "Privacy" },
  { href: "#questions", label: "Questions" },
];

export function Header() {
  const begin = useBegin();
  return (
    <header className="sticky top-0 z-20 bg-ground px-5 sm:px-8 lg:px-12">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6">
        <a href="#top" className="flex items-center gap-2.5 font-display text-2xl">
          <Ember size={26} state="idle" className="text-accent" /> Nova
        </a>
        <nav aria-label="On this page" className="hidden items-center gap-8 md:flex">
          {SECTIONS.map((s) => (
            <a key={s.href} href={s.href} className="text-ink-soft underline-offset-4 hover:text-ink hover:underline">
              {s.label}
            </a>
          ))}
        </nav>
        <Button onClick={begin} className="min-h-10">
          Begin
        </Button>
      </div>
    </header>
  );
}
