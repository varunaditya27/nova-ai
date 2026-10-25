"use client";

import { useRef, type ReactNode } from "react";
import { gsap, MOTION_OK, SplitText, useGSAP } from "@/lib/gsap";

/** A heading that is read as you scroll: each word comes up from the dark in turn. Plain text for anyone who prefers less motion. */
export function ScrubText({
  children,
  className,
}: {
  children: string;
  className?: string;
}): ReactNode {
  const el = useRef<HTMLHeadingElement>(null);
  useGSAP(() => {
    const mm = gsap.matchMedia();
    mm.add(MOTION_OK, () => {
      document.fonts.ready.then(() => {
        const words = SplitText.create(el.current!, { type: "words" }).words;
        gsap.fromTo(
          words,
          { opacity: 0.14 },
          {
            opacity: 1,
            stagger: 0.12,
            ease: "none",
            scrollTrigger: {
              trigger: el.current,
              start: "top 88%",
              end: "top 40%",
              scrub: true,
            },
          },
        );
      });
    });
  });
  return (
    <h2 ref={el} data-scrub className={className}>
      {children}
    </h2>
  );
}
