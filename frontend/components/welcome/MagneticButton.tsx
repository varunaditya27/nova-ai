"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/Button";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

/** A button that leans a little toward the pointer, then settles. Fine pointers only. */
export function MagneticButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  const wrap = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      const el = wrap.current;
      if (!el) return;
      const mm = gsap.matchMedia();
      mm.add(`${MOTION_OK} and (pointer: fine)`, () => {
        const x = gsap.quickTo(el, "x", { duration: 0.6, ease: "power3.out" });
        const y = gsap.quickTo(el, "y", { duration: 0.6, ease: "power3.out" });
        const move = (e: PointerEvent) => {
          const r = el.getBoundingClientRect();
          x((e.clientX - (r.left + r.width / 2)) * 0.28);
          y((e.clientY - (r.top + r.height / 2)) * 0.28);
        };
        const leave = () => (x(0), y(0));
        el.addEventListener("pointermove", move);
        el.addEventListener("pointerleave", leave);
        return () => {
          el.removeEventListener("pointermove", move);
          el.removeEventListener("pointerleave", leave);
        };
      });
    },
    { scope: wrap }
  );

  return (
    <span ref={wrap} className="inline-block">
      <Button onClick={onClick} className="glint min-h-14 px-9 text-[length:var(--text-read)]">
        {children}
      </Button>
    </span>
  );
}
