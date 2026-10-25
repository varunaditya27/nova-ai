"use client";

import { useRef, type ReactNode } from "react";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

/** Moves a block from one offset to another as it crosses the screen. Two neighbours given different speeds read as depth. */
export function Drift({
  children,
  from,
  to,
  className,
}: {
  children: ReactNode;
  from: number;
  to: number;
  className?: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    const mm = gsap.matchMedia();
    mm.add(`${MOTION_OK} and (min-width: 768px)`, () => {
      gsap.fromTo(
        el.current,
        { y: from },
        {
          y: to,
          ease: "none",
          scrollTrigger: {
            trigger: el.current,
            start: "top bottom",
            end: "bottom top",
            scrub: true,
          },
        },
      );
    });
  });
  return (
    <div ref={el} className={className}>
      {children}
    </div>
  );
}
