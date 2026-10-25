"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { motion, useInView } from "motion/react";
import { useReducedMotionSafe } from "@/lib/motion";
import { Tilt } from "@/components/brand/Tilt";
import { cn } from "@/lib/cn";

/*
 * Moving pictures of real screens, drawn with the app's own surfaces. They are decorative (the text
 * beside each one says the same thing), so they are hidden from assistive technology and contain
 * no live controls. Each plays a short loop while it is on screen: the main action, a supporting
 * detail, and a slow settle.
 */
const small = "text-[length:var(--text-small)] text-ink-soft";
const fakeButton = "inline-flex min-h-11 items-center fold-sm px-6 font-medium";

/** Runs `step(n)` every `ms` while the picture is on screen; stays on the final state for reduced motion. */
function useLoop(
  ms: number,
  steps: number,
): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const seen = useInView(ref, { margin: "-15% 0px" });
  const { reduced } = useReducedMotionSafe();
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!seen || reduced) return;
    const id = window.setInterval(() => setN((v) => (v + 1) % steps), ms);
    return () => window.clearInterval(id);
  }, [seen, reduced, ms, steps]);
  return [ref, reduced ? 0 : seen ? n : 0];
}

function Frame({
  children,
  frame,
}: {
  children: ReactNode;
  frame: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <Tilt>
      <div
        ref={frame}
        aria-hidden
        className="tone flex min-h-[17rem] flex-col justify-center gap-4 px-7 py-8 sm:px-9"
      >
        {children}
      </div>
    </Tilt>
  );
}

const fade = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0 },
  transition: { duration: 0.4 },
};

export function MemorySpecimen() {
  const [ref, n] = useLoop(2600, 3);
  const forgotten = n === 2;
  return (
    <Frame frame={ref}>
      <p className={small}>
        {forgotten ? "Forgotten" : "A memory · from three weeks ago"}
      </p>
      <motion.p
        key={forgotten ? "gone" : "kept"}
        {...fade}
        className="read min-h-[3.4rem]"
      >
        {forgotten
          ? "Nova can no longer recall this. Receipt 3F9A21…D2C7E4."
          : "Has a Data Structures exam on Friday, and feels nervous about graphs."}
      </motion.p>
      <p className={small}>
        About: study, exams. Nova treats this as fairly important.
      </p>
      <motion.span
        animate={{
          scale: n === 1 ? 0.94 : 1,
          backgroundColor: n === 1 ? "var(--accent)" : "var(--sunk)",
          color: n === 1 ? "var(--accent-ink)" : "var(--ink)",
        }}
        transition={{ duration: 0.2 }}
        className={cn(fakeButton, "w-fit")}
      >
        Ask Nova to forget this
      </motion.span>
    </Frame>
  );
}

export function CareSpecimen() {
  const [ref, n] = useLoop(1800, 3);
  return (
    <Frame frame={ref}>
      <p className={small}>Nova · Tuesday evening</p>
      <p className="read">
        You’ve been quieter than usual this week. No need to explain. I’m here
        if you want to talk.
      </p>
      <motion.p
        animate={{ y: n >= 1 ? 0 : 6, scale: n >= 1 ? 1 : 0.985 }}
        transition={{ duration: 0.6 }}
        className={small}
      >
        If things ever feel too heavy, Nova will tell you who you can call.
      </motion.p>
      <div className="flex gap-1.5 pt-2">
        {[0, 1, 2].map((d) => (
          <motion.span
            key={d}
            animate={{ scale: n === d ? 1.25 : 1, opacity: n === d ? 1 : 0.35 }}
            className="size-2  bg-accent"
          />
        ))}
      </div>
    </Frame>
  );
}

export function GoalSpecimen() {
  const [ref, n] = useLoop(1500, 4);
  const done = [n >= 0, n >= 1, n >= 3];
  const fill = [0.33, 0.66, 0.66, 1][n];
  return (
    <Frame frame={ref}>
      <p className="read">Finish the Data Structures course</p>
      <div className="ruler h-3 w-full overflow-hidden bg-sunk">
        <motion.div
          animate={{ width: `${fill * 100}%` }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="h-full fold-sm bg-accent"
        />
      </div>
      <ul className="flex flex-col gap-2">
        {["Arrays", "Linked lists", "Graphs"].map((m, i) => (
          <li key={m} className="flex items-center gap-3">
            <motion.span
              animate={{
                scale: done[i] ? [1, 1.18, 1] : 1,
                backgroundColor: done[i] ? "var(--earned)" : "var(--sunk)",
              }}
              transition={{ duration: 0.5 }}
              className="size-4 "
            />
            <span className={done[i] ? "text-ink-soft" : undefined}>{m}</span>
          </li>
        ))}
      </ul>
      <p className={small}>
        Habit: practise three times a week ·{" "}
        {["once", "twice", "twice", "three times"][n]} so far this week
      </p>
    </Frame>
  );
}

export function StorySpecimen() {
  const [ref, n] = useLoop(2200, 2);
  const words = "A week of nerves, and a good ending.".split(" ");
  return (
    <Frame frame={ref}>
      <p className={small}>Chapter · the week of 3 March</p>
      <p
        key={n}
        className="font-display text-[length:var(--text-title)] leading-[1.1]"
      >
        {words.map((w, i) => (
          <motion.span
            key={i}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              delay: i * 0.07,
              duration: 0.5,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="mr-[0.28em] inline-block"
          >
            {w}
          </motion.span>
        ))}
      </p>
      <p className="read text-ink-soft">
        You spent most of it dreading Friday. By Saturday the worry had turned
        into relief, and you were already planning what to do next.
      </p>
    </Frame>
  );
}

export function PeopleSpecimen() {
  const [ref, n] = useLoop(1400, 4);
  return (
    <Frame frame={ref}>
      <div className="flex items-center gap-4">
        <motion.span
          animate={{ scale: n === 0 ? [0.8, 1.08, 1] : 1 }}
          className="grid size-12 place-items-center fold-sm bg-accent font-display text-xl text-accent-ink"
        >
          M
        </motion.span>
        <div>
          <p className="read">Meera</p>
          <p className={small}>
            Your sister · you mention her about twice a week
          </p>
        </div>
      </div>
      <div className="flex items-end gap-1.5 pt-1">
        {[3, 5, 2, 6, 4, 7, 5].map((h, i) => (
          <motion.span
            key={i}
            animate={{ height: (n + i) % 4 === 0 ? h * 5 + 6 : h * 5 }}
            className="w-3 rounded-[2px] bg-earned"
            style={{ height: h * 5 }}
          />
        ))}
      </div>
      <p className="read text-ink-soft">
        Last time: she’s coming to visit after your exams.
      </p>
    </Frame>
  );
}

export function ErrandSpecimen() {
  const [ref, n] = useLoop(1700, 3);
  const done = n === 2;
  return (
    <Frame frame={ref}>
      <p className={small}>Calendar · Nova would like to</p>
      <p className="read">
        Add “Study group” to your calendar on Friday at 4 pm.
      </p>
      <p className={small}>
        {done
          ? "Done. It’s on your calendar, and you can undo it."
          : "You can undo this afterwards."}
      </p>
      <div className="flex gap-3">
        <motion.span
          animate={{
            scale: n === 1 ? 0.93 : 1,
            backgroundColor: done ? "var(--earned)" : "var(--accent)",
            color: done ? "var(--accent-ink)" : "var(--accent-ink)",
          }}
          transition={{ duration: 0.2 }}
          className={fakeButton}
        >
          {done ? "Done" : "Go ahead"}
        </motion.span>
        <span className={cn(fakeButton, "bg-sunk")}>Not now</span>
      </div>
    </Frame>
  );
}
