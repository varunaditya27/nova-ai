"use client";

import { useRef } from "react";
import { Mark } from "@/components/ui/Mark";
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

/** A short title sequence: the stamp is pressed onto the page, the name is set beside it, and the page peels away toward its folded corner. Once per visit. */
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
    tl.from("[data-intro-mark]", {
      scale: 1.35,
      autoAlpha: 0,
      duration: 0.5,
      ease: "power4.in",
    })
      .to("[data-intro-mark]", { y: 2, duration: 0.08, yoyo: true, repeat: 1 })
      .from(
        "[data-intro-name] span",
        { yPercent: 115, stagger: 0.07, duration: 0.8, ease: "power4.out" },
        "-=0.1",
      )
      .to({}, { duration: 0.5 })
      .to("[data-intro-content]", {
        autoAlpha: 0,
        y: -12,
        duration: 0.4,
        ease: "power2.in",
      })
      .to(
        el,
        {
          clipPath: "polygon(100% 0%, 100% 0%, 100% 100%, 0% 0%)",
          duration: 1,
          ease: "expo.inOut",
        },
        "-=0.1",
      );
  });

  return (
    <div
      ref={root}
      data-light="night"
      aria-hidden
      className="fixed inset-0 z-[70] grid place-items-center bg-ground text-ink"
      style={{ clipPath: "polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%)" }}
    >
      <div data-intro-content className="relative flex flex-col items-center gap-6">
        <span data-intro-mark>
          <Mark size={120} />
        </span>
        <p
          data-intro-name
          className="flex overflow-hidden font-display text-5xl tracking-[-0.02em]"
        >
          {"nova".split("").map((c, i) => (
            <span key={i} className="inline-block">
              {c}
            </span>
          ))}
        </p>
      </div>
    </div>
  );
}
