"use client";

import { motion } from "motion/react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { rise, stagger } from "@/lib/motion";
import { useBegin } from "./useBegin";

function Line({ who, children, knot = false }: { who: string; children: string; knot?: boolean }) {
  return (
    <motion.p variants={rise} className="relative">
      {knot && <span aria-hidden className="absolute -left-9 top-2 size-[17px] rounded-full bg-accent" />}
      <span className="block text-[length:var(--text-small)] text-mute">{who}</span>
      {children}
    </motion.p>
  );
}

/** The promise, and proof of it: the same conversation, three weeks apart. */
export function Hero() {
  const begin = useBegin();
  return (
    <motion.section
      id="top"
      variants={stagger(0.09)}
      initial="hidden"
      animate="show"
      className="px-5 pb-20 pt-12 sm:px-8 sm:pb-28 sm:pt-20 lg:px-12"
    >
      <div className="mx-auto max-w-6xl">
        <motion.h1 variants={rise} className="max-w-4xl text-[length:var(--text-display)]">
          A companion that remembers you.
        </motion.h1>
        <div className="mt-12 grid items-start gap-14 lg:grid-cols-12">
      <div className="flex flex-col gap-8 lg:col-span-6">
        <motion.p variants={rise} className="read max-w-xl text-ink-soft">
          Nova is one conversation that goes on for years. It remembers what you tell it, notices how you’re doing, and runs on your own computer, so what you share stays with you.
        </motion.p>
        <motion.div variants={rise} className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <Button onClick={begin}>Begin the conversation</Button>
          <ButtonLink href="#how" variant="text">
            See how it grows
          </ButtonLink>
        </motion.div>
      </div>

      <motion.figure variants={rise} className="lg:col-span-5 lg:col-start-8" aria-label="An example conversation, three weeks apart">
        <div className="tone px-6 py-8 sm:px-8">
          <figcaption className="mb-6 text-[length:var(--text-small)] text-ink-soft">An example, three weeks apart</figcaption>
          <div className="relative flex flex-col gap-6 pl-9">
            <span aria-hidden className="absolute bottom-1 left-[7px] top-1 w-[3px] rounded-full bg-sunk" />
            <Line who="You" knot>
              I have my Data Structures exam on Friday and I keep freezing on graphs.
            </Line>
            <motion.p variants={rise} className="italic text-mute">
              Three weeks pass.
            </motion.p>
            <Line who="You">I got the results back.</Line>
            <Line who="Nova" knot>
              The exam you were dreading, the one with graphs? I’ve been wondering how it went.
            </Line>
          </div>
        </div>
      </motion.figure>
        </div>
      </div>
    </motion.section>
  );
}
