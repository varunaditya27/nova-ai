"use client";

import { useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";
import { Section } from "./Section";

type Id = "you" | "meera" | "exam" | "run" | "mum" | "study";

/** Example life, positioned for a wide stage (x, y in a 1000 × 600 box) and a tall one (600 × 760). */
const NODES: { id: Id; label: string; note: string; wide: [number, number]; tall: [number, number] }[] = [
  { id: "you", label: "You", note: "At the centre of it all is you. Nova only knows what you choose to share.", wide: [500, 300], tall: [300, 380] },
  { id: "meera", label: "Meera", note: "Your sister. She’s coming to visit after your exams.", wide: [170, 150], tall: [110, 130] },
  { id: "exam", label: "The Friday exam", note: "You were nervous about graphs. When the results came back, Nova asked how it went.", wide: [280, 480], tall: [130, 620] },
  { id: "run", label: "Running", note: "You’re happier in the weeks you go running. Nova noticed, and mentions it kindly.", wide: [800, 130], tall: [490, 150] },
  { id: "mum", label: "Mum’s operation", note: "It was on a Thursday. Once she was home, Nova asked how you were holding up.", wide: [860, 440], tall: [490, 600] },
  { id: "study", label: "Study group", note: "Fridays at 4 pm. Nova added it to your calendar after asking you first.", wide: [560, 540], tall: [320, 730] },
];
const EDGES: [Id, Id][] = [["you", "meera"], ["you", "exam"], ["you", "run"], ["you", "mum"], ["you", "study"], ["exam", "study"], ["meera", "mum"]];

/** Memory as a map, not a list. Touch any point in the example life to see what connects to it. */
export function Constellation() {
  const root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState<Id>("you");
  const [tall, setTall] = useState(false);
  const note = NODES.find((n) => n.id === active)!.note;
  const size = tall ? { w: 600, h: 760 } : { w: 1000, h: 600 };
  const at = (id: Id) => NODES.find((n) => n.id === id)![tall ? "tall" : "wide"];

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(max-width: 767px)", () => {
        setTall(true);
        return () => setTall(false);
      });
      mm.add(MOTION_OK, () => {
        const tl = gsap.timeline({ scrollTrigger: { trigger: root.current, start: "top 75%", end: "center 55%", scrub: 0.8 } });
        tl.from("[data-edge]", { strokeDashoffset: 1, stagger: 0.12, duration: 0.6, ease: "none" }, 0)
          .from("[data-node]", { scale: 0, autoAlpha: 0, stagger: 0.1, duration: 0.5, ease: "power3.out", transformOrigin: "50% 50%" }, 0.1);
      });
      mm.add(`${MOTION_OK} and (pointer: fine)`, () => {
        const x = gsap.quickTo("[data-drift]", "x", { duration: 1.2, ease: "power3" });
        const y = gsap.quickTo("[data-drift]", "y", { duration: 1.2, ease: "power3" });
        const move = (e: PointerEvent) => {
          const r = root.current!.getBoundingClientRect();
          x(((e.clientX - r.left) / r.width - 0.5) * -22);
          y(((e.clientY - r.top) / r.height - 0.5) * -16);
        };
        root.current!.addEventListener("pointermove", move);
        return () => root.current?.removeEventListener("pointermove", move);
      });
    },
    { scope: root }
  );

  return (
    <Section id="connects" tone="ink" label="Everything connects" reveal>
      <div className="mb-10 max-w-3xl">
        <h2 className="text-[length:var(--text-title)]">Nothing it learns is on its own.</h2>
        <p className="read mt-5 max-w-2xl opacity-85">
          People, plans and worries link to one another, the way they do in a life. Touch a point in this example to see what it’s connected to.
        </p>
      </div>

      <div ref={root} className="relative mx-auto w-full max-w-5xl" style={{ aspectRatio: `${size.w} / ${size.h}` }}>
        <div data-drift className="absolute inset-0">
          <svg viewBox={`0 0 ${size.w} ${size.h}`} className="absolute inset-0 size-full" aria-hidden>
            {EDGES.map(([a, b]) => {
              const [x1, y1] = at(a);
              const [x2, y2] = at(b);
              const lit = a === active || b === active;
              return (
                <line
                  key={a + b}
                  data-edge
                  x1={x1} y1={y1} x2={x2} y2={y2}
                  pathLength={1}
                  strokeDasharray={1}
                  strokeDashoffset={0}
                  strokeWidth={lit ? 3 : 2}
                  className={cn("transition-[stroke,stroke-width] duration-500", lit ? "stroke-earned" : "stroke-current opacity-30")}
                  style={lit ? undefined : { strokeOpacity: 0.3 }}
                />
              );
            })}
          </svg>
          {NODES.map((n, i) => {
            const [x, y] = at(n.id);
            const on = n.id === active;
            return (
              <div key={n.id} className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${(x / size.w) * 100}%`, top: `${(y / size.h) * 100}%` }}>
                <button
                  data-node
                  onPointerEnter={() => setActive(n.id)}
                  onFocus={() => setActive(n.id)}
                  onClick={() => setActive(n.id)}
                  aria-pressed={on}
                  className={cn(
                    "float-soft flex min-h-11 items-center gap-2.5 whitespace-nowrap rounded-full px-5 transition-colors duration-300",
                    on ? "bg-earned text-[#10302e]" : "bg-[color-mix(in_srgb,var(--ground)_20%,var(--ink))] hover:bg-[color-mix(in_srgb,var(--ground)_32%,var(--ink))]"
                  )}
                  style={{ animationDelay: `${i * -1.3}s` }}
                >
                  <span aria-hidden className={cn("size-3 rounded-full", n.id === "you" ? "bg-accent" : on ? "bg-[#10302e]" : "bg-earned")} />
                  {n.label}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <p aria-live="polite" className="read mx-auto mt-10 min-h-[4.5rem] max-w-2xl text-center">
        {note}
      </p>
    </Section>
  );
}
