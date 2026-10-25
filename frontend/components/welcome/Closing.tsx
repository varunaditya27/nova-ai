"use client";

import { useRef } from "react";
import { LightField } from "@/components/brand/LightField";
import { Ember } from "@/components/ui/Ember";
import { gsap, MOTION_OK, SplitText, useGSAP } from "@/lib/gsap";
import { Section } from "./Section";
import { SECTIONS } from "./Header";
import { MagneticButton } from "@/components/brand/MagneticButton";
import { useBegin } from "./useBegin";

export function Closing() {
  const begin = useBegin();
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        document.fonts.ready.then(() => {
          const split = SplitText.create("[data-close-title]", {
            type: "words",
          });
          gsap.from(split.words, {
            yPercent: 60,
            autoAlpha: 0,
            stagger: 0.12,
            duration: 1,
            ease: "power4.out",
            scrollTrigger: { trigger: root.current, start: "top 70%" },
          });
        });
        gsap.to("[data-close-star]", {
          rotate: 90,
          ease: "none",
          scrollTrigger: {
            trigger: root.current,
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        });
        gsap.from("[data-close-item]", {
          y: 24,
          autoAlpha: 0,
          stagger: 0.1,
          duration: 0.9,
          ease: "power4.out",
          scrollTrigger: { trigger: root.current, start: "top 60%" },
        });
      });
    },
    { scope: root },
  );

  return (
    <>
      <Section label="Begin">
        <div
          ref={root}
          className="relative isolate overflow-hidden cut py-16 sm:px-6"
        >
          <LightField className="pointer-events-none absolute inset-0 -z-10 size-full opacity-70" />
          <span
            aria-hidden
            data-close-star
            className="pointer-events-none absolute -right-24 top-1/2 -translate-y-1/2 text-accent opacity-15 sm:-right-10"
          >
            <Ember size={520} />
          </span>
          <div className="relative flex flex-col items-start gap-8">
            <h2 data-close-title className="text-[length:var(--text-display)]">
              Say the first thing.
            </h2>
            <p data-close-item className="read max-w-xl text-ink-soft">
              There’s nothing to sign up for. Start whenever you like.
            </p>
            <div data-close-item>
              <MagneticButton onClick={begin}>
                Begin the conversation
              </MagneticButton>
            </div>
          </div>
        </div>
      </Section>
      <footer className="px-5 pb-12 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6">
          <p className="flex items-center gap-2.5 font-display text-2xl">
            <Ember size={24} className="text-accent" /> Nova
          </p>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-8 gap-y-2">
            {SECTIONS.map((s) => (
              <a
                key={s.href}
                href={s.href}
                className="inline-flex min-h-11 items-center text-ink-soft underline-offset-4 hover:text-ink hover:underline"
              >
                {s.label}
              </a>
            ))}
          </nav>
        </div>
      </footer>
    </>
  );
}
