"use client";

import { useRef, type ReactNode } from "react";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

/** A panel that turns a few degrees toward the pointer, with a pool of light that follows it. Mouse only; still otherwise. */
export function Tilt({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const el = root.current!;
      const mm = gsap.matchMedia();
      mm.add(`${MOTION_OK} and (pointer: fine)`, () => {
        const rx = gsap.quickTo(el, "rotationX", {
          duration: 0.7,
          ease: "power3",
        });
        const ry = gsap.quickTo(el, "rotationY", {
          duration: 0.7,
          ease: "power3",
        });
        const move = (e: PointerEvent) => {
          const r = el.getBoundingClientRect();
          const px = (e.clientX - r.left) / r.width;
          const py = (e.clientY - r.top) / r.height;
          ry((px - 0.5) * 9);
          rx((0.5 - py) * 7);
          el.style.setProperty("--lx", `${px * 100}%`);
          el.style.setProperty("--ly", `${py * 100}%`);
          el.style.setProperty("--lo", "1");
        };
        const leave = () => {
          rx(0);
          ry(0);
          el.style.setProperty("--lo", "0");
        };
        gsap.set(el, { transformPerspective: 1100 });
        el.addEventListener("pointermove", move);
        el.addEventListener("pointerleave", leave);
        return () => {
          el.removeEventListener("pointermove", move);
          el.removeEventListener("pointerleave", leave);
        };
      });
    },
    { scope: root },
  );

  return (
    <div
      ref={root}
      className={`relative [transform-style:preserve-3d] ${className ?? ""}`}
    >
      {children}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 fold opacity-[var(--lo,0)] transition-opacity duration-500"
        style={{
          background:
            "radial-gradient(420px circle at var(--lx,50%) var(--ly,50%), rgb(255 255 255 / 0.28), transparent 60%)",
          mixBlendMode: "soft-light",
        }}
      />
    </div>
  );
}
