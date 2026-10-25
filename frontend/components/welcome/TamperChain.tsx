"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/cn";

const RECORDS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

/** Tamper-evidence you can try: change any record and see everything after it stop matching. */
export function TamperChain() {
  const [changed, setChanged] = useState<number | null>(null);
  return (
    <div className="mt-16">
      <p className="font-display text-[length:var(--text-read)]">
        Try it: change one record.
      </p>
      <ol className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-0">
        {RECORDS.map((day, i) => {
          const broken = changed !== null && i > changed;
          const edited = changed === i;
          return (
            <li
              key={day}
              className="flex flex-1 items-center sm:last:flex-none"
            >
              <motion.button
                onClick={() => setChanged(edited ? null : i)}
                aria-pressed={edited}
                whileTap={{ scale: 0.95 }}
                animate={{ rotate: edited ? [0, -3, 3, -2, 0] : 0 }}
                className={cn(
                  "min-h-14 w-full fold px-5 text-left sm:w-auto sm:min-w-[7.5rem]",
                  edited
                    ? "bg-[#ff8a80] text-accent-ink"
                    : broken
                      ? "bg-[color-mix(in_srgb,var(--ground)_20%,var(--ink))] text-[#ff8a80]"
                      : "bg-[color-mix(in_srgb,var(--ground)_20%,var(--ink))]",
                )}
              >
                <span className="block text-[length:var(--text-small)] opacity-80">
                  Record {i + 1}
                </span>
                {day}
                <span className="sr-only">
                  {edited
                    ? ", changed"
                    : broken
                      ? ", no longer matches"
                      : ", matches"}
                </span>
              </motion.button>
              {i < RECORDS.length - 1 && (
                <span
                  aria-hidden
                  className="hidden h-[3px] min-w-6 flex-1 sm:block"
                >
                  <motion.span
                    className="block h-full fold-sm"
                    animate={{
                      backgroundColor:
                        changed !== null && i >= changed
                          ? "#ff8a80"
                          : "var(--earned)",
                      opacity: changed !== null && i >= changed ? 0.55 : 1,
                    }}
                    style={
                      changed !== null && i >= changed
                        ? {
                            backgroundImage:
                              "repeating-linear-gradient(90deg, transparent 0 6px, var(--ink) 6px 10px)",
                          }
                        : undefined
                    }
                  />
                </span>
              )}
            </li>
          );
        })}
      </ol>
      <p aria-live="polite" className="read mt-6 max-w-2xl opacity-90">
        {changed === null
          ? "Each record is sealed to the one before it. Choose any record to pretend someone altered it."
          : `Record ${changed + 1} was altered. ${changed === RECORDS.length - 1 ? "It no longer matches its seal" : "It and every record after it no longer match their seals"}, so the change is caught.`}
      </p>
    </div>
  );
}
