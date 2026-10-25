"use client";

import { useRef } from "react";
import { Ember } from "@/components/ui/Ember";
import { gsap, MOTION_OK, ScrollTrigger, useGSAP } from "@/lib/gsap";

const WORDS = ["Remembers", "Notices", "Follows through", "Keeps your story"];

/** The four things Nova does, as a slow ribbon. Scrolling hurries it and leans it into the direction of travel. */
export function Marquee() {
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const drift = gsap.to("[data-track]", {
          xPercent: -50,
          duration: 46,
          ease: "none",
          repeat: -1,
        });
        const skew = gsap.quickTo("[data-track]", "skewX", {
          duration: 0.6,
          ease: "power3",
        });
        ScrollTrigger.create({
          trigger: root.current,
          start: "top bottom",
          end: "bottom top",
          onUpdate: (self) => {
            const v = self.getVelocity();
            skew(gsap.utils.clamp(-9, 9, v / -260));
            drift.timeScale(1 + Math.min(5, Math.abs(v) / 260));
          },
        });
      });
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      aria-hidden
      className="overflow-hidden bg-sunk py-10 text-ink sm:py-14"
    >
      <div
        data-track
        className="flex w-max items-center gap-10 whitespace-nowrap font-display text-[length:clamp(3rem,1.5rem+6.5vw,8.5rem)] leading-none"
      >
        {[0, 1].flatMap((set) =>
          WORDS.map((w, i) => (
            <span key={`${set}-${w}`} className="flex items-center gap-10">
              <span className={i % 2 ? "outline-text" : undefined}>{w}</span>
              <Ember size={56} className="shrink-0 text-accent" />
            </span>
          )),
        )}
      </div>
    </section>
  );
}
