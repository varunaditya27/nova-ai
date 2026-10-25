"use client";

import { SectionHead } from "./Section";

import { useRef, useState } from "react";
import { ScrubFilm, type ScrubHandle } from "@/components/brand/ScrubFilm";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";
import type { Light } from "@/components/ThemeProvider";

const STAGES: { label: string; light: Light; knows: string[]; acts: string }[] =
  [
    {
      label: "The first day",
      light: "dawn",
      knows: ["Only what you’ve just said."],
      acts: "Nova listens more than it talks. It asks very little, doesn’t bring up the past, and won’t message you first while it learns how you like to talk.",
    },
    {
      label: "Three weeks in",
      light: "day",
      knows: [
        "Your name, and what you’re studying.",
        "The exam on Friday, and how nervous you were.",
        "That your sister is called Meera.",
      ],
      acts: "After about five conversations Nova opens up. It refers back to what you’ve told it, and checks in on things that matter to you.",
    },
    {
      label: "Six months in",
      light: "dusk",
      knows: [
        "Around twenty-five weekly chapters of your story.",
        "That you talk most on Sunday evenings.",
        "That you’re happier in the weeks you go running.",
      ],
      acts: "Nova starts to notice patterns, and mentions them gently, as something it has seen rather than a verdict.",
    },
    {
      label: "Two years in",
      light: "night",
      knows: [
        "The people who matter, and how often you speak of them.",
        "The moments you marked as mattering.",
        "Every goal you’ve set, finished or let go.",
      ],
      acts: "Nova can look back with you: on anniversaries, and at the end of a year, on how far you’ve come.",
    },
  ];

/**
 * Memory is the product, and it builds slowly, so this section is paced by your scroll. As the
 * months pass the light in the room moves from dawn to night. On a phone, or if you prefer less
 * motion, the four stages simply sit one after another.
 */
export function Growth() {
  const root = useRef<HTMLElement>(null);
  const film = useRef<ScrubHandle>(null);
  const [pinned, setPinned] = useState(false);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(`${MOTION_OK} and (min-width: 1024px)`, () => {
        const el = root.current!;
        el.dataset.pinned = "true";
        setPinned(true);
        const panels = gsap.utils.toArray<HTMLElement>("[data-stage]");
        gsap.set(panels.slice(1), { opacity: 0 });

        const tl = gsap.timeline({
          defaults: { ease: "power2.inOut" },
          scrollTrigger: {
            trigger: el,
            start: "top top",
            end: "+=260%",
            pin: "[data-pin]",
            anticipatePin: 1,
            scrub: 0.7,
            onUpdate: (self) => {
              const i = Math.min(3, Math.round(self.progress * 3));
              el.dataset.light = STAGES[i].light;
              film.current?.seek(self.progress);
            },
          },
        });
        panels.forEach((p, i) => {
          if (i === 0) return;
          tl.to(
            panels[i - 1],
            { opacity: 0, y: -28, duration: 0.45 },
            i - 0.55,
          ).fromTo(
            p,
            { opacity: 0, y: 32 },
            { opacity: 1, y: 0, duration: 0.55 },
            i - 0.35,
          );
        });
        return () => {
          delete el.dataset.pinned;
          setPinned(false);
          el.dataset.light = STAGES[0].light;
        };
      });
    },
    { scope: root },
  );

  return (
    <section
      id="how"
      ref={root}
      aria-label="How it grows"
      data-light="dawn"
      className="group bg-ground text-ink transition-colors duration-700"
    >
      <div
        data-pin
        className="px-5 py-20 sm:px-8 sm:py-28 lg:flex lg:min-h-dvh lg:items-center lg:px-12 lg:py-16"
      >
        <div className="mx-auto w-full max-w-6xl">
          <SectionHead n="03" name="How it grows" />
          <h2 className="max-w-3xl text-[length:var(--text-title)]">
            It gets to know you slowly.
          </h2>
          <p className="read mt-4 max-w-2xl text-ink-soft">
            Nova doesn’t pretend to know you on day one. This is what knowing
            someone looks like as time passes, for an example person.
          </p>

          <div className="mt-12 grid gap-12 lg:grid-cols-12">
            <div
              aria-hidden
              className="hidden lg:col-span-5 lg:group-data-[pinned=true]:block"
            >
              <div className="aspect-square overflow-hidden fold bg-[#151210]">
                <ScrubFilm
                  ref={film}
                  frames={120}
                  src={(i) => `/film/growth/${String(i).padStart(3, "0")}.webp`}
                  active={pinned}
                  className="size-full"
                />
              </div>
            </div>

            <div className="flex flex-col gap-16 lg:col-span-12 lg:group-data-[pinned=true]:col-span-7 lg:group-data-[pinned=true]:grid lg:group-data-[pinned=true]:gap-0">
              {STAGES.map((s) => (
                <div
                  key={s.label}
                  data-stage
                  className="lg:group-data-[pinned=true]:col-start-1 lg:group-data-[pinned=true]:row-start-1"
                >
                  <h3 className="font-display text-[length:var(--text-display)] leading-[0.95] lg:group-data-[pinned=true]:text-[length:var(--text-title)]">
                    {s.label}
                  </h3>
                  <div className="mt-6 grid gap-4 md:grid-cols-2 lg:group-data-[pinned=true]:grid-cols-1">
                    <div className="tone px-7 py-7 sm:px-9">
                      <p className="font-display text-[length:var(--text-read)]">
                        What Nova knows
                      </p>
                      <ul className="read mt-4 flex flex-col gap-3">
                        {s.knows.map((k) => (
                          <li key={k} className="relative pl-6">
                            <span
                              aria-hidden
                              className="absolute left-0 top-[0.7em] size-2.5  bg-accent"
                            />
                            {k}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="tone-sunk px-7 py-7 sm:px-9">
                      <p className="font-display text-[length:var(--text-read)]">
                        How it behaves
                      </p>
                      <p className="read mt-4">{s.acts}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
