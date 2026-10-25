"use client";

import { useRef } from "react";
import { Section } from "./Section";
import { gsap, MOTION_OK, ScrollTrigger, SplitText, useGSAP } from "@/lib/gsap";

const BEATS = [
  { who: "You", text: "I have my Data Structures exam on Friday and I keep freezing on graphs." },
  { who: "Three weeks pass", text: "" },
  { who: "You", text: "I got the results back." },
  { who: "Nova", text: "The exam you were dreading, the one with graphs? I’ve been wondering how it went." },
];

/** The promise, proved: one conversation, three weeks apart. The thread draws as you scroll, and Nova's reply is read as it arrives. */
export function ThreadProof() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const wide = window.matchMedia("(min-width: 1024px)").matches;
        const line = root.current!.querySelector("[data-line]");
        const words = SplitText.create("[data-nova-line]", { type: "words", aria: "none" }).words;
        const days = gsap.utils.toArray<HTMLElement>("[data-day]");

        const tl = gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: { trigger: root.current, start: "top 70%", end: "bottom 55%", scrub: 0.8 },
        });
        tl.fromTo(line, wide ? { scaleX: 0 } : { scaleY: 0 }, wide ? { scaleX: 1, duration: 4 } : { scaleY: 1, duration: 4 }, 0);
        gsap.utils.toArray<HTMLElement>("[data-beat]").forEach((el, i) => {
          tl.from(el, { autoAlpha: 0, y: 24, duration: 0.6, ease: "power3.out" }, i * 1.05);
          tl.from(el.querySelector("[data-knot]"), { scale: 0, duration: 0.4, ease: "power3.out" }, i * 1.05);
        });
        tl.from(days, { scale: 0, duration: 0.05, stagger: 0.04 }, 1.1);
        tl.fromTo(words, { opacity: 0.12 }, { opacity: 1, stagger: 0.12, duration: 0.3 }, 3.1);
        return () => ScrollTrigger.getAll().forEach((s) => s.trigger === root.current && s.kill());
      });
    },
    { scope: root }
  );

  return (
    <Section id="proof" label="An example, three weeks apart">
      <h2 className="mb-14 max-w-2xl text-[length:var(--text-title)]">The same conversation, three weeks apart.</h2>
      <div ref={root} className="relative lg:pt-12">
        <span aria-hidden data-line className="absolute bottom-0 left-[7px] top-0 w-[3px] origin-top rounded-full bg-accent lg:bottom-auto lg:left-0 lg:right-0 lg:top-[7px] lg:h-[3px] lg:w-full lg:origin-left" />
        <span aria-hidden className="absolute bottom-0 left-[7px] top-0 -z-10 w-[3px] rounded-full bg-sunk lg:bottom-auto lg:left-0 lg:right-0 lg:top-[7px] lg:h-[3px] lg:w-full" />
        <ol className="grid gap-10 pl-10 lg:grid-cols-4 lg:gap-8 lg:pl-0">
          {BEATS.map((b, i) => (
            <li key={i} data-beat className="relative">
              <span aria-hidden data-knot className="absolute -left-10 top-1 size-[17px] rounded-full bg-accent lg:-top-12 lg:left-0 lg:size-[17px]" />
              <p className="text-[length:var(--text-small)] text-mute">{b.who}</p>
              {i === 1 ? (
                <div aria-hidden className="mt-3 grid max-w-[11rem] grid-cols-7 gap-1.5">
                  {Array.from({ length: 21 }, (_, d) => (
                    <span key={d} data-day className="size-4 rounded-full bg-earned" />
                  ))}
                </div>
              ) : (
                <p {...(i === 3 ? { "data-nova-line": true } : {})} className={i === 3 ? "font-display text-[length:var(--text-read)] leading-snug" : "read mt-1"}>
                  {b.text}
                </p>
              )}
            </li>
          ))}
        </ol>
      </div>
    </Section>
  );
}
