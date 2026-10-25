"use client";

import { Mark } from "@/components/ui/Mark";
import { useAwake } from "@/lib/hooks/useHealth";

/** Whether Nova can be reached right now — in plain words, so a failure never reads as a mystery. */
export function Pulse() {
  const { awake, checking } = useAwake();
  if (checking)
    return (
      <p className="text-[length:var(--text-small)] text-mute">Checking in…</p>
    );
  return (
    <p
      className="flex items-start gap-2 text-[length:var(--text-small)] text-ink-soft"
      role="status"
    >
      <Mark size={16} quiet={!awake} className="mt-0.5" />
      <span>
        {awake
          ? "Nova is here"
          : "Nova is resting. Your words are safe; try again in a moment."}
      </span>
    </p>
  );
}
