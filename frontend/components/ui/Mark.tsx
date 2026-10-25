"use client";

import {
  useCallback,
  useEffect,
  useRef,
  type CSSProperties,
} from "react";
import { motion, useAnimate, useMotionValue, useSpring } from "motion/react";
import { cn } from "@/lib/cn";
import { useReducedMotionSafe } from "@/lib/motion";
import { leanDegrees } from "@/lib/companion/lean";
import { useWatchPointer } from "@/lib/companion/presence";
import type { Mood } from "@/lib/voice";

/**
 * Nova's mark: a bookplate. A maroon square with its corner folded over, the way you dog-ear a page you
 * mean to come back to, and a single italic "n" set in it. It is the same stamp on every reply Nova writes
 * (the way a letter is signed), in the sidebar, on the favicon, and as the pressed corner every surface on
 * the site carries.
 *
 * It is also Nova's body. It has no face; like a desk lamp in a short film, it has character through how it
 * moves. Calm it breathes. Thinking it pulses, pressed again and again. Happy it hops. Asleep it tilts and
 * drifts a "z". Startled it jumps. Lost it looks about. With `alive` it leans toward your pointer and hops
 * when you say hello. Everything stops under reduced motion, and the mood is carried by shape alone.
 */
export function Mark({
  size = 24,
  mood = "calm",
  alive = false,
  cheer = 0,
  quiet = false,
  className,
  label,
}: {
  /** Pixels, or any CSS length. */
  size?: number | string;
  mood?: Mood;
  /** Leans toward the pointer, hops when you hover it, breathes while calm. For the main places Nova lives. */
  alive?: boolean;
  /** Change this number to make the stamp hop once (a reply arrived, something was saved). */
  cheer?: number;
  /** Muted, for places where Nova is absent (an error, a page that isn't there). */
  quiet?: boolean;
  className?: string;
  /** Accessible name; omit when purely decorative. */
  label?: string;
}) {
  const { reduced } = useReducedMotionSafe();
  const [body, animate] = useAnimate<HTMLSpanElement>();
  const outer = useRef<HTMLSpanElement>(null);
  const turn = useMotionValue(0);
  const lean = useSpring(turn, { stiffness: 140, damping: 18, mass: 0.6 });
  const lastHop = useRef(0);

  useWatchPointer(
    alive && !reduced && mood !== "sleepy",
    useCallback(
      (p) => {
        const r = outer.current?.getBoundingClientRect();
        if (!r) return;
        turn.set(
          leanDegrees({ x: r.x + r.width / 2, y: r.y + r.height / 2 }, p),
        );
      },
      [turn],
    ),
  );

  const hop = useCallback(() => {
    if (reduced || !body.current) return;
    lastHop.current = Date.now();
    animate(
      body.current,
      { y: [0, -9, 0, -3, 0], scaleY: [1, 1.06, 0.92, 1.02, 1] },
      { duration: 0.6, ease: "easeOut" },
    );
  }, [animate, body, reduced]);

  /** Say hello by hovering: it hops, but not more than once every couple of seconds. */
  const greet = useCallback(() => {
    if (Date.now() - lastHop.current > 2500) hop();
  }, [hop]);

  useEffect(() => {
    if (cheer > 0) hop();
  }, [cheer, hop]);

  useEffect(() => {
    const el = body.current;
    if (!el || reduced) return;
    const loop = (frames: Record<string, number[] | number>, seconds: number) =>
      animate(el, frames, {
        duration: seconds,
        repeat: Infinity,
        ease: "easeInOut",
      });
    const run = {
      calm: () =>
        alive
          ? loop({ scale: [1, 1.035, 1], rotate: [0, -1.4, 0] }, 5)
          : animate(el, { scale: 1, rotate: 0, opacity: 1 }, { duration: 0.3 }),
      thinking: () => loop({ scale: [1, 0.9, 1] }, 1.5),
      happy: () => {
        hop();
        return animate(el, { scale: 1, rotate: 0 }, { duration: 0.3 });
      },
      sleepy: () => {
        animate(el, { rotate: 8, opacity: 0.88 }, { duration: 0.8 });
        return loop({ scale: [0.96, 0.985, 0.96] }, 6);
      },
      startled: () =>
        animate(
          el,
          { scale: [1, 1.18, 1], rotate: [0, -7, 0], opacity: 1 },
          { duration: 0.4, ease: "easeOut" },
        ),
      lost: () => loop({ rotate: [-7, 7, -7] }, 3.2),
    }[mood]();
    return () => run.stop();
  }, [mood, alive, reduced, animate, body, hop]);

  const len = typeof size === "number" ? `${size}px` : size;
  const style = {
    width: len,
    height: len,
    fontSize: `calc(${len} * 0.7)`,
    "--c": `calc(${len} * 0.3)`,
  } as CSSProperties;
  return (
    <motion.span
      ref={outer}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      data-mood={mood}
      className="relative inline-block shrink-0"
      style={{ width: len, height: len, rotate: lean }}
      onPointerEnter={alive ? greet : undefined}
    >
      <span
        ref={body}
        className={cn(
          "fold grid size-full place-items-center font-display font-bold italic leading-none",
          quiet ? "bg-sunk text-mute" : "bg-accent text-accent-ink",
          className,
        )}
        style={style}
      >
        <span aria-hidden className="-translate-y-[0.04em]">
          n
        </span>
      </span>
      {mood === "sleepy" && !reduced && (
        <motion.span
          aria-hidden
          className="hand pointer-events-none absolute -right-[0.35em] -top-[0.5em] text-[0.55em] leading-none text-mute"
          animate={{ y: [0, -6], opacity: [0, 1, 0] }}
          transition={{ duration: 2.6, repeat: Infinity, ease: "easeOut" }}
        >
          z
        </motion.span>
      )}
    </motion.span>
  );
}

/** The name, set plainly: no effects, no ligature, in the display face. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "font-display font-bold leading-none tracking-[-0.02em]",
        className,
      )}
    >
      Nova
    </span>
  );
}

/** The stamp and the name together. */
export function Lockup({
  className,
  mood,
  alive,
}: {
  className?: string;
  mood?: Mood;
  alive?: boolean;
}) {
  return (
    <span className={cn("inline-flex items-center gap-[0.35em]", className)}>
      <Mark size="1.05em" mood={mood} alive={alive} />
      <Wordmark />
    </span>
  );
}
