"use client";

import { useEffect, useRef } from "react";
import { gsap } from "@/lib/gsap";
import { classify, worthFraming, type CursorMode } from "@/lib/cursor/classify";
import { framePath } from "@/lib/cursor/frame";
import { dampStep, trailLength } from "@/lib/cursor/physics";
import { drawTrail, type Point } from "@/lib/cursor/trail";
import { useCursorPreference } from "@/lib/cursor/preference";

/** A line of handwriting, written and unwritten again and again while Nova is composing. */
const WRITING = "M2 15 C5 6 7 6 9 13 S13 21 16 11 S21 5 26 13 S31 19 34 9";

/**
 * Nova's cursor is a pen: an ink dot that is exactly where you point, a ring that follows a
 * beat behind and stretches with speed, and an ink line drawn behind that lengthens the faster you move.
 * It changes with what it is over:
 *   press    the dot shrinks and a bracket with bitten corners closes around the thing you can press,
 *            in that thing's own colour; destructive actions get a dashed bracket
 *   blocked  the bracket goes dotted and faint and the dot is struck through
 *   read     the dot narrows to a line, like a caret, over text
 *   film     the dot becomes a point of light over the opening shot
 *   field    steps aside so the real text cursor shows where you type
 * While Nova is thinking (html[data-busy]) the dot gives way to a line of handwriting, written and unwritten. It
 * breathes when you stop, ripples when you press, and goes away when you leave the window. Mouse and
 * pen only. Under reduced motion it follows exactly, with no thread, spin or ripple. It can be
 * switched off in the sidebar.
 */
export function NovaCursor() {
  const [enabled] = useCursorPreference();
  const root = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const bracket = useRef<SVGSVGElement>(null);
  const outline = useRef<SVGPathElement>(null);
  const dotPlace = useRef<HTMLDivElement>(null);
  const ringPlace = useRef<HTMLDivElement>(null);
  const breath = useRef<HTMLDivElement>(null);
  const dot = useRef<HTMLSpanElement>(null);
  const ring = useRef<HTMLSpanElement>(null);
  const bar = useRef<HTMLSpanElement>(null);
  const slash = useRef<HTMLSpanElement>(null);
  const wound = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!enabled || !window.matchMedia("(pointer: fine)").matches) return;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const html = document.documentElement;
    const R = root.current!,
      cv = canvas.current!,
      ctx = cv.getContext("2d")!;
    const [bkt, path, dp, rp, brt, dt_, rg, br, sl, wd] = [
      bracket.current!,
      outline.current!,
      dotPlace.current!,
      ringPlace.current!,
      breath.current!,
      dot.current!,
      ring.current!,
      bar.current!,
      slash.current!,
      wound.current!,
    ];

    const target: Point = { x: -100, y: -100 };
    const pos: Point = { x: -100, y: -100 };
    const lag: Point = { x: -100, y: -100 };
    const vel: Point = { x: 0, y: 0 };
    const trail: Point[] = [];
    const frame = { x: 0, y: 0, w: 40, h: 40, o: 0 };
    let mode: CursorMode = "default";
    let el: Element | null = null;
    let danger = false;
    let awake = false;
    let busy = false;
    let idle: gsap.core.Tween | null = null;
    let idleTimer = 0;
    let spin: gsap.core.Tween | null = null;
    let color = "#800000";
    const dpr = Math.min(2, window.devicePixelRatio || 1);

    const size = () => {
      cv.width = innerWidth * dpr;
      cv.height = innerHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const readColor = () =>
      (color =
        getComputedStyle(html).getPropertyValue("--accent").trim() || color);
    const to = (t: gsap.TweenTarget, v: gsap.TweenVars) =>
      gsap.to(t, {
        duration: reduced ? 0 : 0.4,
        ease: "power3.out",
        overwrite: "auto",
        ...v,
      });
    const dotSize = (m: CursorMode) =>
      m === "press"
        ? 0.45
        : m === "blocked"
          ? 0.7
          : m === "film"
            ? 1.9
            : m === "read"
              ? 0.4
              : 1;

    const apply = (next: CursorMode) => {
      mode = next;
      R.dataset.mode = next;
      const is = (...m: CursorMode[]) => m.includes(next);
      to(R, { opacity: next === "field" ? 0 : 1, duration: 0.2 });
      to(dt_, {
        scale: dotSize(next),
        opacity: is("read") || busy ? 0 : is("blocked") ? 0.5 : 1,
        backgroundColor: is("film") ? "#fbbf24" : "",
      });
      to(rg, {
        scale: is("press", "read") ? 0.2 : is("film") ? 1.9 : 1,
        opacity: is("press", "read", "blocked") || busy ? 0 : 0.55,
      });
      to(br, {
        opacity: is("read") && !busy ? 1 : 0,
        scaleY: is("read") ? 1 : 0.2,
      });
      to(sl, {
        opacity: is("blocked") ? 1 : 0,
        scale: is("blocked") ? 1 : 0.4,
      });
      to(frame, {
        o: is("press", "blocked") ? 1 : 0,
        duration: reduced ? 0 : 0.35,
      });
      dt_.style.boxShadow = is("film") ? "0 0 14px 4px #fbbf24" : "";
    };

    const winding = (on: boolean) => {
      busy = on;
      spin?.kill();
      spin = null;
      to(wd, { opacity: on ? 1 : 0, scale: on ? 1 : 0.4 });
      const line = wd.querySelector("path")!;
      if (on && !reduced)
        spin = gsap.fromTo(
          line,
          { strokeDashoffset: 1 },
          {
            strokeDashoffset: -1,
            duration: 1.8,
            ease: "power1.inOut",
            repeat: -1,
          },
        );
      else gsap.set(line, { strokeDashoffset: 0 });
      apply(mode);
    };

    const measure = () => {
      if (!el || !(mode === "press" || mode === "blocked")) return null;
      const b = el.getBoundingClientRect();
      if (!worthFraming(b)) return null;
      return { x: b.left - 6, y: b.top - 6, w: b.width + 12, h: b.height + 12 };
    };

    const wake = () => {
      clearTimeout(idleTimer);
      idle?.kill();
      idle = null;
      gsap.to(brt, { scale: 1, duration: 0.3, overwrite: "auto" });
      if (!reduced)
        idleTimer = window.setTimeout(
          () =>
            (idle = gsap.to(brt, {
              scale: 1.25,
              duration: 1.1,
              ease: "sine.inOut",
              yoyo: true,
              repeat: -1,
            })),
          2200,
        );
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      target.x = e.clientX;
      target.y = e.clientY;
      if (!awake) {
        awake = true;
        Object.assign(pos, target);
        Object.assign(lag, target);
        html.classList.add("nova-cursor");
        R.style.visibility = "visible";
      }
      const t = classify(e.target as Element | null);
      const changed = t.mode !== mode || t.el !== el;
      el = t.el;
      danger = t.danger;
      if (changed) {
        path.style.stroke = t.danger
          ? "var(--danger)"
          : el
            ? getComputedStyle(el).color
            : color;
        path.style.strokeDasharray = t.danger
          ? "5 4"
          : t.mode === "blocked"
            ? "2 4"
            : "";
        if ((t.mode === "press" || t.mode === "blocked") && frame.o < 0.05)
          Object.assign(frame, { x: pos.x - 6, y: pos.y - 6, w: 12, h: 12 });
        apply(t.mode);
      }
      wake();
    };
    const onDown = () => {
      if (!awake || mode === "field") return;
      to(dt_, { scale: dotSize(mode) * 0.6, duration: 0.12 });
      if (reduced) return;
      const ripple = document.createElement("span");
      ripple.className =
        "absolute left-0 top-0 size-8 rounded-full border-[1.5px]";
      ripple.style.cssText = `border-color:${danger ? "var(--danger)" : color};margin:-16px 0 0 -16px;transform:translate(${pos.x}px,${pos.y}px)`;
      R.appendChild(ripple);
      gsap.fromTo(
        ripple,
        { scale: 0.3, opacity: 0.9 },
        {
          scale: 2.4,
          opacity: 0,
          duration: 0.7,
          ease: "power3.out",
          onComplete: () => ripple.remove(),
        },
      );
    };
    const onUp = () => awake && apply(mode);
    const hide = () => to(R, { opacity: 0, duration: 0.25 });
    const show = () =>
      awake && mode !== "field" && to(R, { opacity: 1, duration: 0.25 });
    const watch = () => {
      readColor();
      const b = html.dataset.busy === "true";
      if (b !== busy) winding(b);
    };

    const tick = (_: number, ms: number) => {
      const dt = Math.min(0.05, ms / 1000);
      const rect = measure();
      const aim = rect
        ? { x: rect.x + rect.w / 2, y: rect.y + rect.h / 2 }
        : target;
      if (reduced) {
        Object.assign(pos, aim);
        Object.assign(lag, aim);
      } else {
        [pos.x, vel.x] = dampStep(pos.x, vel.x, aim.x, rect ? 16 : 40, dt);
        [pos.y, vel.y] = dampStep(pos.y, vel.y, aim.y, rect ? 16 : 40, dt);
        lag.x = dampStep(lag.x, 0, pos.x, 13, dt)[0];
        lag.y = dampStep(lag.y, 0, pos.y, 13, dt)[0];
      }
      const speed = Math.hypot(vel.x, vel.y);
      gsap.set(dp, { x: pos.x, y: pos.y });
      gsap.set(rp, {
        x: lag.x,
        y: lag.y,
        rotation: (Math.atan2(vel.y, vel.x) * 180) / Math.PI,
        scaleX: reduced ? 1 : 1 + Math.min(0.9, speed / 2400),
      });

      ctx.clearRect(0, 0, cv.width, cv.height);
      if (!reduced && !busy && (mode === "default" || mode === "film")) {
        trail.push({ x: lag.x, y: lag.y });
        while (
          trail.length >
          Math.max(2, trailLength(speed) * (mode === "film" ? 1.6 : 1))
        )
          trail.shift();
        drawTrail(ctx, trail, mode === "film" ? "#fbbf24" : color, 5);
      } else trail.length = 0;

      if (rect) {
        for (const k of ["x", "y", "w", "h"] as const)
          frame[k] = reduced
            ? rect[k]
            : dampStep(frame[k], 0, rect[k], 26, dt)[0];
        path.setAttribute("d", framePath(frame.w, frame.h));
        bkt.style.transform = `translate(${frame.x}px, ${frame.y}px)`;
      }
      bkt.style.opacity = rect
        ? String(frame.o * (mode === "blocked" ? 0.5 : 1))
        : "0";
    };

    R.style.visibility = "hidden";
    size();
    readColor();
    gsap.set(wd, { opacity: 0 });
    const mo = new MutationObserver(watch);
    mo.observe(html, {
      attributes: true,
      attributeFilter: ["data-light", "data-busy"],
    });
    watch();
    gsap.ticker.add(tick);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("resize", size);
    html.addEventListener("mouseleave", hide);
    html.addEventListener("mouseenter", show);
    return () => {
      gsap.ticker.remove(tick);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("resize", size);
      html.removeEventListener("mouseleave", hide);
      html.removeEventListener("mouseenter", show);
      mo.disconnect();
      idle?.kill();
      spin?.kill();
      clearTimeout(idleTimer);
      html.classList.remove("nova-cursor");
    };
  }, [enabled]);

  if (!enabled) return null;
  return (
    <div
      ref={root}
      aria-hidden
      data-mode="default"
      data-nova-cursor
      className="pointer-events-none fixed inset-0 z-[100] text-accent"
    >
      <canvas ref={canvas} className="absolute inset-0 size-full" />
      <svg
        ref={bracket}
        width="1"
        height="1"
        className="absolute left-0 top-0 overflow-visible opacity-0"
      >
        <path
          ref={outline}
          fill="none"
          strokeWidth="1.75"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div ref={ringPlace} className="absolute left-0 top-0">
        <div className="-translate-x-1/2 -translate-y-1/2">
          <span
            ref={ring}
            className="block size-7 rounded-full border-[1.5px] border-current opacity-55"
          />
        </div>
      </div>
      <div ref={dotPlace} className="absolute left-0 top-0">
        <div ref={breath} className="-translate-x-1/2 -translate-y-1/2">
          <div className="relative grid size-6 place-items-center">
            <span
              ref={dot}
              className="block size-[9px] rounded-full bg-accent shadow-[0_0_0_1.5px_var(--ground)]"
            />
            <span
              ref={bar}
              className="absolute h-7 w-[2px] bg-accent opacity-0 shadow-[0_0_0_1px_var(--ground)]"
            />
            <span
              ref={slash}
              className="absolute h-[2px] w-7 -rotate-45 bg-danger opacity-0"
            />
            <svg
              ref={wound}
              viewBox="0 0 36 24"
              className="absolute h-6 w-9 overflow-visible opacity-0"
            >
              <path
                d={WRITING}
                pathLength={1}
                strokeDasharray={1}
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
