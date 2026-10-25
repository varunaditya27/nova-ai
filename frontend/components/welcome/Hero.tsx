"use client";

import { useRef } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";
import { HeroFilm } from "./HeroFilm";
import { introWillPlay } from "./Intro";
import { MagneticButton } from "./MagneticButton";
import { useBegin } from "./useBegin";

const LINES = ["A companion ", "that remembers ", "you."];

/**
 * The opening shot: a day passing over one life, filling the frame, with the promise set over it in
 * very large type. The camera pushes in as you scroll, and a pool of light follows the pointer.
 */
export function Hero() {
  const begin = useBegin();
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const el = root.current!;
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const tl = gsap.timeline({ delay: introWillPlay() ? 2.45 : 0.15 });
        tl.from("[data-hero-film]", { scale: 1.3, autoAlpha: 0, duration: 2.6, ease: "power3.out" }, 0)
          .from("[data-hero-line]", { yPercent: 118, duration: 1.4, stagger: 0.14, ease: "power4.out" }, 0.2)
          .from("[data-hero-item]", { y: 32, autoAlpha: 0, duration: 1, stagger: 0.1, ease: "power4.out" }, 1.1);

        gsap.to("[data-hero-push]", { scale: 1.3, yPercent: 10, ease: "none", scrollTrigger: { trigger: el, start: "top top", end: "bottom top", scrub: true } });
        gsap.to("[data-hero-copy]", { yPercent: -14, autoAlpha: 0.1, ease: "none", scrollTrigger: { trigger: el, start: "top top", end: "bottom 30%", scrub: true } });
      });
      mm.add(`${MOTION_OK} and (pointer: fine)`, () => {
        const pos = { x: el.clientWidth * 0.68, y: el.clientHeight * 0.4 };
        const paint = () => {
          el.style.setProperty("--mx", `${pos.x}px`);
          el.style.setProperty("--my", `${pos.y}px`);
        };
        paint();
        const move = (e: PointerEvent) => {
          const r = el.getBoundingClientRect();
          gsap.to(pos, { x: e.clientX - r.left, y: e.clientY - r.top, duration: 1.1, ease: "power3.out", overwrite: true, onUpdate: paint });
        };
        el.addEventListener("pointermove", move);
        return () => el.removeEventListener("pointermove", move);
      });
    },
    { scope: root }
  );

  return (
    <section
      id="top"
      ref={root}
      data-light="night"
      className="relative isolate flex min-h-dvh items-end overflow-hidden bg-[#06151a] px-5 pb-16 pt-32 text-ink sm:px-8 sm:pb-24 lg:px-12"
    >
      <div data-hero-film aria-hidden className="pointer-events-none absolute inset-0 -z-20 overflow-hidden">
        <div data-hero-push className="size-full lg:translate-x-[11%]">
          <HeroFilm className="size-full object-cover [object-position:63%_50%]" />
        </div>
      </div>
      <div aria-hidden className="absolute inset-0 -z-10" style={{ background: "linear-gradient(90deg, rgb(6 21 26 / 0.78) 0%, rgb(6 21 26 / 0.35) 48%, transparent 75%)" }} />
      <div aria-hidden className="absolute inset-0 -z-10" style={{ background: "radial-gradient(520px circle at var(--mx, 68%) var(--my, 40%), rgb(255 179 71 / 0.14), transparent 62%)" }} />
      <div aria-hidden className="absolute inset-x-0 bottom-0 -z-10 h-1/2" style={{ background: "linear-gradient(to top, #06151a 5%, transparent)" }} />

      <div data-hero-copy className="mx-auto w-full max-w-6xl">
        <h1 className="text-[length:clamp(3.1rem,0.4rem+9vw,9.5rem)] leading-[0.92] tracking-[-0.035em]">
          {LINES.map((l) => (
            <span key={l} className="block overflow-hidden pb-[0.12em]">
              <span data-hero-line className="block">
                {l}
              </span>
            </span>
          ))}
        </h1>
        <div className="mt-10 grid items-end gap-10 lg:grid-cols-12">
          <p data-hero-item className="read max-w-lg text-ink-soft lg:col-span-5">
            Nova is one conversation that goes on for years. It remembers what you tell it, notices how you’re doing, and runs on your own computer, so what you share stays with you.
          </p>
          <div data-hero-item className="flex flex-wrap items-center gap-x-7 gap-y-4 lg:col-span-7 lg:justify-end">
            <MagneticButton onClick={begin}>Begin the conversation</MagneticButton>
            <ButtonLink href="#proof" variant="text">
              See it in action
            </ButtonLink>
          </div>
        </div>
      </div>
    </section>
  );
}
