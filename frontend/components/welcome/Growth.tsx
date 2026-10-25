"use client";

import { useRef } from "react";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";
import type { Light } from "@/components/ThemeProvider";

const STAGES: { label: string; light: Light; knows: string[]; acts: string }[] = [
  {
    label: "The first day",
    light: "dawn",
    knows: ["Only what you’ve just said."],
    acts: "Nova listens more than it talks. It asks very little, doesn’t bring up the past, and won’t message you first while it learns how you like to talk.",
  },
  {
    label: "Three weeks in",
    light: "day",
    knows: ["Your name, and what you’re studying.", "The exam on Friday, and how nervous you were.", "That your sister is called Meera."],
    acts: "After about five conversations Nova opens up. It refers back to what you’ve told it, and checks in on things that matter to you.",
  },
  {
    label: "Six months in",
    light: "dusk",
    knows: ["Around twenty-five weekly chapters of your story.", "That you talk most on Sunday evenings.", "That you’re happier in the weeks you go running."],
    acts: "Nova starts to notice patterns, and mentions them gently, as something it has seen rather than a verdict.",
  },
  {
    label: "Two years in",
    light: "night",
    knows: ["The people who matter, and how often you speak of them.", "The moments you marked as mattering.", "Every goal you’ve set, finished or let go."],
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

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(`${MOTION_OK} and (min-width: 1024px)`, () => {
        const el = root.current!;
        el.dataset.pinned = "true";
        const panels = gsap.utils.toArray<HTMLElement>("[data-stage]");
        const knots = gsap.utils.toArray<HTMLElement>("[data-stage-knot]");
        gsap.set(panels.slice(1), { autoAlpha: 0 });
        gsap.set(knots[0], { scale: 1.6, backgroundColor: "var(--accent)" });

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
            },
          },
        });
        tl.fromTo("[data-stage-line]", { scaleY: 0 }, { scaleY: 1, ease: "none", duration: 3 }, 0);
        panels.forEach((p, i) => {
          if (i === 0) return;
          tl.to(panels[i - 1], { autoAlpha: 0, y: -28, duration: 0.45 }, i - 0.55)
            .fromTo(p, { autoAlpha: 0, y: 32 }, { autoAlpha: 1, y: 0, duration: 0.55 }, i - 0.35)
            .to(knots[i], { scale: 1.6, backgroundColor: "var(--accent)", duration: 0.3 }, i - 0.3);
        });
        return () => {
          delete el.dataset.pinned;
          el.dataset.light = STAGES[0].light;
        };
      });
    },
    { scope: root }
  );

  return (
    <section
      id="how"
      ref={root}
      aria-label="How it grows"
      data-light="dawn"
      className="group bg-ground text-ink transition-colors duration-700"
    >
      <div data-pin className="px-5 py-20 sm:px-8 sm:py-28 lg:flex lg:min-h-dvh lg:items-center lg:px-12 lg:py-16">
        <div className="mx-auto w-full max-w-6xl">
          <h2 className="max-w-3xl text-[length:var(--text-title)]">It gets to know you slowly.</h2>
          <p className="read mt-4 max-w-2xl text-ink-soft">
            Nova doesn’t pretend to know you on day one. This is what knowing someone looks like as time passes, for an example person.
          </p>

          <div className="mt-12 grid gap-12 lg:grid-cols-12">
            <div aria-hidden className="relative hidden lg:col-span-1 lg:group-data-[pinned=true]:block">
              <span className="absolute bottom-2 left-[7px] top-2 w-[3px] rounded-full bg-sunk" />
              <span data-stage-line className="absolute bottom-2 left-[7px] top-2 w-[3px] origin-top rounded-full bg-accent" />
              <div className="relative flex h-full min-h-[22rem] flex-col justify-between">
                {STAGES.map((s) => (
                  <span key={s.label} data-stage-knot className="size-[17px] rounded-full bg-sunk" />
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-16 lg:col-span-11 lg:group-data-[pinned=true]:grid lg:group-data-[pinned=true]:gap-0">
              {STAGES.map((s) => (
                <div key={s.label} data-stage className="lg:group-data-[pinned=true]:col-start-1 lg:group-data-[pinned=true]:row-start-1">
                  <h3 className="font-display text-[length:var(--text-display)] leading-[0.95]">{s.label}</h3>
                  <div className="mt-8 grid gap-5 md:grid-cols-2">
                    <div className="tone px-7 py-7 sm:px-9">
                      <p className="font-display text-[length:var(--text-read)]">What Nova knows</p>
                      <ul className="read mt-4 flex flex-col gap-3">
                        {s.knows.map((k) => (
                          <li key={k} className="relative pl-6">
                            <span aria-hidden className="absolute left-0 top-[0.7em] size-2.5 rounded-full bg-accent" />
                            {k}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="tone-sunk px-7 py-7 sm:px-9">
                      <p className="font-display text-[length:var(--text-read)]">How it behaves</p>
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
