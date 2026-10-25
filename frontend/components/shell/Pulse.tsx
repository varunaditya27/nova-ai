"use client";

import { Ember } from "@/components/ui/Ember";
import { useAwake } from "@/lib/hooks/useHealth";

/** Whether Nova can be reached right now — in plain words, so a failure never reads as a mystery. */
export function Pulse() {
  const { awake, checking } = useAwake();
  if (checking) return <p className="text-[length:var(--text-small)] text-mute">Checking in…</p>;
  return (
    <p className="flex items-start gap-2 text-[length:var(--text-small)] text-ink-soft" role="status">
      <Ember size={14} state={awake ? "idle" : "still"} className={awake ? "mt-1 text-accent" : "mt-1 text-mute"} />
      <span>{awake ? "Nova is here" : "Nova is resting. Your words are safe; try again in a moment."}</span>
    </p>
  );
}
