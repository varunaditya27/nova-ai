"use client";

import { CloudSun, Cloud, Sun, Moon } from "lucide-react";
import type { ComponentType } from "react";
import { relativeTime } from "@/lib/time";

// "Weather" is a metaphor for the state of the relationship, not the sky.
const WEATHER: Record<string, { icon: ComponentType<{ size?: number }>; word: string }> = {
  sunny: { icon: Sun, word: "warm" },
  clear: { icon: CloudSun, word: "clear" },
  cloudy: { icon: Cloud, word: "quiet" },
  distant: { icon: Moon, word: "distant" },
};

/** One quiet ambient line: how things stand, and when you last spoke. */
export function Weather({
  weather,
  stage,
  lastInteraction,
}: {
  weather: string;
  stage: string;
  lastInteraction: string | null;
}) {
  const w = WEATHER[weather] ?? WEATHER.clear;
  const Icon = w.icon;
  const since = relativeTime(lastInteraction);
  return (
    <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
      <Icon size={13} />
      <span>{w.word}</span>
      <span aria-hidden>·</span>
      <span>{stage.replace(/_/g, " ")}</span>
      {since && (
        <>
          <span aria-hidden>·</span>
          <span>last spoke {since}</span>
        </>
      )}
    </div>
  );
}
