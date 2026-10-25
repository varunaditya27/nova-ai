"use client";

import { useRef } from "react";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

const HOT = "a, button, summary, [role='radio'], [role='tab']";

/** A small dot that is exactly where the pointer is, and a ring that follows a beat behind and opens over anything you can press. Mouse only. */
export function Cursor() {
  const dot = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    const mm = gsap.matchMedia();
    mm.add(`${MOTION_OK} and (pointer: fine)`, () => {
      const d = dot.current!;
      const r = ring.current!;
      gsap.set([d, r], { xPercent: -50, yPercent: -50, autoAlpha: 0 });
      const dx = gsap.quickTo(d, "x", { duration: 0.08, ease: "none" });
      const dy = gsap.quickTo(d, "y", { duration: 0.08, ease: "none" });
      const rx = gsap.quickTo(r, "x", { duration: 0.55, ease: "power3" });
      const ry = gsap.quickTo(r, "y", { duration: 0.55, ease: "power3" });
      const move = (e: PointerEvent) => {
        dx(e.clientX);
        dy(e.clientY);
        rx(e.clientX);
        ry(e.clientY);
        const hot = Boolean((e.target as Element | null)?.closest(HOT));
        gsap.to([d, r], { autoAlpha: 1, duration: 0.3, overwrite: "auto" });
        gsap.to(r, { scale: hot ? 1.9 : 1, borderWidth: hot ? 1 : 1.5, duration: 0.5, ease: "power3.out", overwrite: "auto" });
        gsap.to(d, { scale: hot ? 0.4 : 1, duration: 0.3, overwrite: "auto" });
      };
      const gone = () => gsap.to([d, r], { autoAlpha: 0, duration: 0.3 });
      window.addEventListener("pointermove", move);
      document.addEventListener("pointerleave", gone);
      return () => {
        window.removeEventListener("pointermove", move);
        document.removeEventListener("pointerleave", gone);
      };
    });
  });

  return (
    <div aria-hidden className="pointer-events-none fixed left-0 top-0 z-[60] mix-blend-difference">
      <div ref={dot} className="fixed left-0 top-0 size-1.5 rounded-full bg-white" />
      <div ref={ring} className="fixed left-0 top-0 size-9 rounded-full border-[1.5px] border-white" />
    </div>
  );
}
