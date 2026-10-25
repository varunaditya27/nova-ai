"use client";

import { useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { gsap, ScrollTrigger, useGSAP } from "@/lib/gsap";

const CHAPTERS = [
  { id: "top", label: "Opening" },
  { id: "proof", label: "The proof" },
  { id: "how", label: "How it grows" },
  { id: "connects", label: "How it connects" },
  { id: "does", label: "What it does" },
  { id: "light", label: "The light" },
  { id: "private", label: "Privacy" },
  { id: "questions", label: "Questions" },
];

/**
 * Where you are in the page: a thin ruler down the right edge with a marker that rides it as you scroll,
 * and a stop for each chapter. It is the page's contents list and its progress bar in one, so a long
 * scroll never feels lost. Shown once the opening shot has passed, on wide screens.
 */
export function ChapterRail() {
  const root = useRef<HTMLElement>(null);
  const [active, setActive] = useState("top");

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1280px)", () => {
        // The chapter you are in is the last one whose top has passed the middle of the screen.
        const track = ScrollTrigger.create({
          start: 0,
          end: "max",
          onUpdate: () => {
            const mid = window.innerHeight * 0.55;
            const here = CHAPTERS.filter(
              (c) =>
                (document.getElementById(c.id)?.getBoundingClientRect().top ??
                  Infinity) <= mid,
            ).pop();
            setActive(here?.id ?? "top");
            const shown = window.scrollY > window.innerHeight * 0.8;
            gsap.to(root.current, {
              autoAlpha: shown ? 1 : 0,
              x: shown ? 0 : 12,
              duration: 0.6,
              ease: "power3.out",
              overwrite: "auto",
            });
          },
        });
        gsap.set(root.current, { autoAlpha: 0 });
        const marker = gsap.to("[data-rail-marker]", {
          top: "100%",
          ease: "none",
          scrollTrigger: {
            trigger: document.body,
            start: "top top",
            end: "bottom bottom",
            scrub: 0.4,
          },
        });
        const fill = gsap.fromTo(
          "[data-rail-fill]",
          { scaleY: 0 },
          {
            scaleY: 1,
            ease: "none",
            scrollTrigger: {
              trigger: document.body,
              start: "top top",
              end: "bottom bottom",
              scrub: 0.4,
            },
          },
        );
        return () =>
          [track, marker.scrollTrigger, fill.scrollTrigger].forEach((t) =>
            t?.kill(),
          );
      });
    },
    { scope: root },
  );

  return (
    <nav
      ref={root}
      aria-label="Chapters"
      className="invisible fixed right-6 top-1/2 z-30 hidden h-[min(26rem,60vh)] -translate-y-1/2 xl:block"
    >
      <span
        aria-hidden
        className="absolute bottom-0 right-[5px] top-0 w-[2px] bg-sunk"
      />
      <span
        aria-hidden
        data-rail-fill
        className="absolute bottom-0 right-[5px] top-0 w-[2px] origin-top bg-accent"
      />
      <span
        aria-hidden
        data-rail-marker
        className="absolute right-0 top-0 h-[3px] w-3 -translate-y-1/2 bg-earned"
      />
      <ul className="relative flex h-full flex-col justify-between">
        {CHAPTERS.map((c) => (
          <li key={c.id} className="group flex items-center justify-end gap-3">
            <a
              href={`#${c.id}`}
              aria-current={active === c.id ? "true" : undefined}
              className={cn(
                "fold-sm bg-raised px-3 py-1 text-[length:var(--text-small)] opacity-0 transition-opacity duration-300 group-hover:opacity-100 focus-visible:opacity-100",
                active === c.id && "opacity-100",
              )}
            >
              {c.label}
            </a>
            <span
              aria-hidden
              className={cn(
                "relative z-10 mr-[3px] size-[7px] transition-all duration-300",
                active === c.id ? "scale-150 bg-accent" : "bg-mute",
              )}
            />
          </li>
        ))}
      </ul>
    </nav>
  );
}
