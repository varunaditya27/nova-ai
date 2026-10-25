"use client";

import { useRef, type ReactNode } from "react";
import { Margin } from "@/components/brand/Margin";
import { MagneticButton } from "@/components/brand/MagneticButton";
import type { Light } from "@/components/ThemeProvider";
import { ButtonLink } from "@/components/ui/Button";
import { Mark } from "@/components/ui/Mark";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";
import { dayLight, heroHour } from "@/lib/welcome/dayLight";
import { HeroLight } from "./HeroLight";
import { HeroRuler } from "./HeroRuler";
import { SHADE_END, beamX, openingScore, pagePeel, scrollScore } from "./heroScore";
import { useBegin } from "./useBegin";

const SKIP_EVENTS = ["pointerdown", "keydown", "wheel", "touchstart"];

const Line = ({ children }: { children: ReactNode }) => (
  <span className="block overflow-hidden pb-[0.12em]">
    <span data-hero-line className="block motion-safe:opacity-0">
      {children}
    </span>
  </span>
);

/**
 * The opening: a page, in the light of the visitor's real hour. A window's light crosses it from first
 * light and lands on "now"; the promise is set; the stamp lands. The page is dog-eared (`fold`), and as
 * you leave it the fold grows across the page. The score lives in heroScore.ts.
 */
export function Hero() {
  const begin = useBegin();
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const el = root.current!;
      const q = gsap.utils.selector(el);
      const d = new Date();
      const shown = document.documentElement.dataset.light as Light;
      const now = dayLight(heroHour(shown, d.getHours() + d.getMinutes() / 60));
      el.style.setProperty("--at", String(now.at));

      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const tl = openingScore(el, dayLight(5.5), now);
        const skip = () => tl.progress(1);
        SKIP_EVENTS.forEach((e) => window.addEventListener(e, skip, { once: true, passive: true }));
        scrollScore(el, now);
        return () => SKIP_EVENTS.forEach((e) => window.removeEventListener(e, skip));
      });
      mm.add("(prefers-reduced-motion: reduce)", () => {
        gsap.set(q("[data-hero-beam]"), { xPercent: beamX(now.at), skewX: now.skew, opacity: now.strength, color: now.tint });
        gsap.set(q("[data-hero-shade]"), { opacity: SHADE_END });
      });
      mm.add(`${MOTION_OK} and (min-width: 768px)`, () => pagePeel(el));
      mm.add(`${MOTION_OK} and (pointer: fine)`, () => {
        const lean = gsap.quickTo(q("[data-hero-beam]"), "x", { duration: 1.1, ease: "power3" });
        const move = (e: PointerEvent) => lean((e.clientX / window.innerWidth - 0.5) * -16);
        el.addEventListener("pointermove", move);
        return () => el.removeEventListener("pointermove", move);
      });
    },
    { scope: root },
  );

  return (
    <section
      id="top"
      ref={root}
      className="fold relative isolate flex min-h-dvh items-end overflow-hidden bg-ground px-5 pb-16 pt-32 [--c:56px] [clip-path:polygon(0_0,calc(100%-var(--c))_0,100%_var(--c),100%_calc(100%-var(--p,0px)),calc(100%-var(--p,0px))_100%,0_100%)] sm:px-8 sm:pb-24 lg:px-12 lg:[--c:88px]"
    >
      <HeroLight />
      <HeroRuler />
      <span
        aria-hidden
        className="pointer-events-none absolute bottom-0 right-0 z-20 h-[var(--p,0px)] w-[var(--p,0px)] [filter:drop-shadow(-4px_-4px_8px_rgb(20_12_8/0.25))]"
        style={{ background: "linear-gradient(to bottom right, var(--raised), var(--surface) 49.5%, transparent 50%)" }}
      />

      <div data-hero-copy className="relative z-10 mx-auto w-full max-w-6xl">
        {/* The stamp sits beside the widest line of the headline, outside the heading so its "n" is not part of the heading's text. */}
        <div className="relative w-fit">
          <h1 className="text-[length:clamp(3.1rem,0.4rem+9vw,9.5rem)] leading-[0.92] tracking-[-0.035em]">
            <Line>A companion </Line>
            <Line>
              that{" "}
              <span className="relative inline-block">
                remembers
                <svg
                  aria-hidden
                  viewBox="0 0 300 14"
                  preserveAspectRatio="none"
                  className="absolute -bottom-[0.02em] left-0 h-[0.1em] w-full overflow-visible text-accent"
                >
                  <path
                    data-hero-ink-line
                    d="M2 9 C 40 3, 90 12, 150 7 S 250 4, 298 8"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="6"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
              </span>{" "}
            </Line>
            <Line>you.</Line>
          </h1>
          <div
            aria-hidden
            className="pointer-events-none absolute bottom-full right-0 mb-5 lg:-top-2 lg:bottom-auto lg:left-full lg:right-auto lg:mb-0 lg:ml-[clamp(1rem,2.5vw,2.5rem)]"
          >
            <div className="-rotate-6">
              <div data-hero-stamp className="relative motion-safe:opacity-0">
                <span
                  data-hero-ink
                  className="absolute inset-[-35%] rounded-full opacity-0"
                  style={{ background: "radial-gradient(closest-side, color-mix(in srgb, var(--accent) 38%, transparent), transparent)" }}
                />
                <span data-hero-shadow className="absolute inset-x-[6%] -bottom-[6%] h-[14%] rounded-[50%] bg-[#140c08] opacity-50 blur-xl" />
                <Mark size="clamp(6rem, 10.5vw, 11rem)" />
              </div>
            </div>
          </div>
        </div>
        <div className="mt-10 grid items-end gap-10 lg:grid-cols-12">
          <p data-hero-item className="read max-w-lg text-ink-soft motion-safe:opacity-0 lg:col-span-5">
            Nova is one conversation that goes on for years. It remembers what
            you tell it, notices how you’re doing, and runs on your own
            computer, so what you share stays with you.
          </p>
          <div
            data-hero-item
            className="flex flex-wrap items-center gap-x-7 gap-y-4 motion-safe:opacity-0 lg:col-span-7 lg:justify-end"
          >
            <MagneticButton onClick={begin}>Begin the conversation</MagneticButton>
            <ButtonLink href="#proof" variant="text">
              See it in action
            </ButtonLink>
            <Margin tilt={-4} delay={2.6} className="hidden sm:inline-block">
              no sign-up, just hello
            </Margin>
          </div>
        </div>
      </div>
    </section>
  );
}
