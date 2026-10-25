"use client";

import { useRef } from "react";
import { Ember } from "@/components/ui/Ember";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

const KEY = "nova-intro";

/** True when the title sequence will play (first visit this session, motion allowed). The hero waits for it. */
export function introWillPlay(): boolean {
  try {
    return !sessionStorage.getItem(KEY) && window.matchMedia(MOTION_OK).matches;
  } catch {
    return false;
  }
}

/** A short title sequence: the star ignites on black, the name appears, and the curtain lifts onto the page. Once per visit. */
export function Intro() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    const el = root.current!;
    if (!introWillPlay()) {
      el.style.display = "none";
      return;
    }
    try {
      sessionStorage.setItem(KEY, "1");
    } catch {
      /* private mode */
    }
    document.documentElement.style.overflow = "hidden";
    const tl = gsap.timeline({
      onComplete: () => {
        document.documentElement.style.overflow = "";
        el.style.display = "none";
      },
    });
    tl.from("[data-intro-star]", { scale: 0, rotate: -180, duration: 1.1, ease: "power4.out" })
      .from("[data-intro-glow]", { scale: 0.2, autoAlpha: 0, duration: 1.4, ease: "power2.out" }, 0)
      .from("[data-intro-name] span", { yPercent: 110, stagger: 0.07, duration: 0.8, ease: "power4.out" }, 0.55)
      .to({}, { duration: 0.35 })
      .to("[data-intro-name]", { autoAlpha: 0, y: -12, duration: 0.4, ease: "power2.in" })
      .to("[data-intro-star]", { scale: 0.18, duration: 0.5, ease: "power3.in" }, "<")
      .to(el, { yPercent: -100, duration: 1, ease: "expo.inOut" }, "-=0.1");
  });

  return (
    <div ref={root} data-light="night" aria-hidden className="fixed inset-0 z-[70] grid place-items-center bg-[#050f12] text-[#e6f1ea]">
      <span data-intro-glow className="absolute size-[60vmin] rounded-full" style={{ background: "radial-gradient(circle, rgb(255 143 175 / 0.35), transparent 65%)" }} />
      <div className="relative flex flex-col items-center gap-6">
        <span data-intro-star className="text-[#ff8faf]">
          <Ember size={96} />
        </span>
        <p data-intro-name className="flex overflow-hidden font-display text-5xl">
          {"Nova".split("").map((c, i) => (
            <span key={i} className="inline-block">
              {c}
            </span>
          ))}
        </p>
      </div>
    </div>
  );
}
