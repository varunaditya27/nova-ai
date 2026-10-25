"use client";

import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Ember } from "@/components/ui/Ember";
import { Button } from "@/components/ui/Button";
import { rise, stagger } from "@/lib/motion";

const DOES = [
  {
    title: "It remembers",
    body: "Not every word — what matters: your news, your worries, the people in your life. You can read all of it, and make Nova forget any of it.",
  },
  {
    title: "It notices",
    body: "How you’re writing, when you’ve gone quiet, when something sounds heavy. If you’re struggling it checks in, and tells you who you can call.",
  },
  {
    title: "It follows through",
    body: "Tell it a goal and it breaks it into steps and counts your habits. It can set reminders and add calendar events — after asking you first.",
  },
  {
    title: "It stays yours",
    body: "It runs on this computer, so nothing you say is sent to a company. Every record is sealed so that any tampering would show.",
  },
];

/** The front door: what Nova is, what it will and won't do, and how the first days go. */
export default function Welcome() {
  const router = useRouter();
  const begin = () => {
    try {
      localStorage.setItem("nova-welcomed", "1");
    } catch {
      /* private mode: still let them in */
    }
    router.push("/");
  };

  return (
    <div>
      <motion.section
        variants={stagger(0.09)}
        initial="hidden"
        animate="show"
        className="mx-auto flex min-h-dvh max-w-6xl flex-col justify-center gap-12 px-5 py-14 sm:px-8 lg:px-12"
      >
        <motion.p variants={rise} className="flex items-center gap-3 font-display text-3xl">
          <Ember size={32} state="idle" className="text-accent" /> Nova
        </motion.p>
        <motion.h1 variants={rise} className="max-w-5xl text-[length:var(--text-display)]">
          A companion that remembers you.
        </motion.h1>
        <div className="grid items-start gap-12 lg:grid-cols-12">
          <div className="flex flex-col gap-7 lg:col-span-6">
            <motion.p variants={rise} className="read max-w-xl">
              Nova is one conversation that continues for years. It remembers what you tell it, notices how you’re doing, and runs entirely on your own computer.
            </motion.p>
            <motion.div variants={rise}>
              <Button onClick={begin}>Begin the conversation</Button>
            </motion.div>
          </div>

          <motion.div variants={rise} className="lg:col-span-5 lg:col-start-8" aria-label="An example of a conversation weeks apart">
            <div className="tone px-6 py-7">
              <p className="mb-5 text-[length:var(--text-small)] text-ink-soft">An example, three weeks apart</p>
              <div className="relative flex flex-col gap-6 pl-9">
                <span aria-hidden className="absolute bottom-1 left-[7px] top-1 w-[3px] rounded-full bg-sunk" />
                <p className="relative">
                  <span aria-hidden className="absolute -left-9 top-2 size-[17px] rounded-full bg-accent" />
                  <span className="block text-[length:var(--text-small)] text-mute">You</span>
                  I have my Data Structures exam on Friday and I keep freezing on graphs.
                </p>
                <p className="italic text-mute">3 weeks pass.</p>
                <p>
                  <span className="block text-[length:var(--text-small)] text-mute">You</span>
                  I got the results back.
                </p>
                <p>
                  <span className="block text-[length:var(--text-small)] text-mute">Nova</span>
                  The exam you were dreading — the one with graphs? I’ve been wondering how it went.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.section>

      <section className="mx-auto max-w-6xl px-5 py-24 sm:px-8 lg:px-12" aria-labelledby="does">
        <h2 id="does" className="mb-14 max-w-2xl text-[length:var(--text-title)]">What Nova does</h2>
        <ul className="grid gap-x-16 gap-y-12 md:grid-cols-2">
          {DOES.map((d, i) => (
            <li key={d.title} className={i % 2 === 1 ? "md:mt-14" : undefined}>
              <h3 className="font-display text-[length:var(--text-title)] leading-[1.1]">{d.title}</h3>
              <p className="read mt-3 max-w-md">{d.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-ink px-5 py-24 text-ground sm:px-8 lg:px-12" aria-labelledby="not">
        <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-2">
          <h2 id="not" className="text-[length:var(--text-title)]">What Nova is not</h2>
          <p className="read max-w-xl">
            Nova is software, not a person, and it can be wrong. It won’t pretend to feel things it doesn’t, it won’t simply tell you what you want to hear, and when it disagrees it will say so kindly. If you’re in danger, it will point you to people who can help — it isn’t a replacement for them.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-24 sm:px-8 lg:px-12" aria-labelledby="first">
        <div className="grid gap-10 lg:grid-cols-12">
          <h2 id="first" className="text-[length:var(--text-title)] lg:col-span-5">How the first days go</h2>
          <div className="read flex flex-col gap-4 lg:col-span-7">
            <p>
              For the first few conversations Nova stays quiet and gentle. It asks little, doesn’t bring up anything from the past, and won’t reach out first, while it learns how you like to talk.
            </p>
            <p>After roughly five conversations it opens up: it starts referring back to what you’ve told it, and checking in on what matters to you.</p>
            <div className="pt-4">
              <Button onClick={begin}>Begin the conversation</Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
