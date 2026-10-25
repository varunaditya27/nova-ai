"use client";

import { Margin } from "@/components/brand/Margin";
import { useRef, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

const TONES = {
  ground: "",
  sunk: "bg-sunk",
  ink: "bg-ink text-ground",
} as const;

/** One band of the page: a full-width tone, with content held to the same column as every other page. */
export function Section({
  id,
  tone = "ground",
  label,
  children,
  className,
  reveal = false,
}: {
  id?: string;
  tone?: keyof typeof TONES;
  /** Accessible name; the section's visible heading should be what this says. */
  label?: string;
  children: ReactNode;
  className?: string;
  /** Opens from a rounded card to full width as it scrolls into view. */
  reveal?: boolean;
}) {
  const el = useRef<HTMLElement>(null);
  useGSAP(() => {
    if (!reveal) return;
    const mm = gsap.matchMedia();
    mm.add(MOTION_OK, () => {
      gsap.fromTo(
        el.current,
        { clipPath: "inset(7% 3%)" },
        {
          clipPath: "inset(0% 0%)",
          ease: "none",
          scrollTrigger: {
            trigger: el.current,
            start: "top 95%",
            end: "top 25%",
            scrub: true,
          },
        },
      );
    });
  });
  return (
    <section
      ref={el}
      id={id}
      aria-label={label}
      className={cn(
        "scroll-mt-16 px-5 py-20 sm:px-8 sm:py-28 lg:px-12",
        TONES[tone],
      )}
    >
      <div className={cn("mx-auto max-w-6xl", className)}>{children}</div>
    </section>
  );
}

export { Reveal } from "@/components/brand/Reveal";

/** The editorial header of a chapter: a rule, its number, its name. The same names the chapter rail uses. */
export function SectionHead({
  n,
  name,
  note,
}: {
  n: string;
  name: string;
  /** Nova's handwritten aside about this chapter. */
  note?: string;
}) {
  return (
    <div className="rule-top mb-12 flex flex-wrap items-baseline gap-x-5 gap-y-1 pt-4">
      <span className="font-display text-[length:var(--text-read)]">{n}</span>
      <span className="label">{name}</span>
      {note && <Margin className="ml-auto">{note}</Margin>}
    </div>
  );
}
