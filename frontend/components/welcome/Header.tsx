"use client";

import { useState } from "react";
import {
  motion,
  useMotionValueEvent,
  useScroll,
  useSpring,
} from "motion/react";
import { Lockup } from "@/components/ui/Mark";
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
  const { scrollY, scrollYProgress } = useScroll();
  const [over, setOver] = useState(true);
  useMotionValueEvent(scrollY, "change", (y) =>
    setOver(y < window.innerHeight * 0.8),
  );
  const thread = useSpring(scrollYProgress, {
    stiffness: 140,
    damping: 30,
    mass: 0.6,
  });
  return (
    <header
      data-light={over ? "night" : undefined}
      className={`fixed inset-x-0 top-0 z-40 px-5 text-ink transition-colors duration-500 sm:px-8 lg:px-12 ${over ? "bg-transparent" : "bg-ground"}`}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6">
        <a href="#top" aria-label="Nova">
          <Lockup className="text-[1.7rem]" />
        </a>
        <nav
          aria-label="On this page"
          className="hidden items-center gap-8 md:flex"
        >
          {SECTIONS.map((s) => (
            <a
              key={s.href}
              href={s.href}
              className="text-ink-soft underline-offset-4 hover:text-ink hover:underline"
            >
              {s.label}
            </a>
          ))}
        </nav>
        <Button onClick={begin} className="min-h-10">
          Begin
        </Button>
      </div>
      <motion.span
        aria-hidden
        style={{ scaleX: thread }}
        className="absolute inset-x-0 bottom-0 h-[3px] origin-left bg-accent"
      />
    </header>
  );
}
