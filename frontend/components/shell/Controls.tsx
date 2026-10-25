"use client";

import { Volume2, VolumeX } from "lucide-react";
import { useLight, type LightMode } from "@/components/ThemeProvider";
import { useAcoustics } from "@/lib/hooks/useAcoustics";
import { cn } from "@/lib/cn";

const MODES: { value: LightMode; label: string; hint: string }[] = [
  { value: "auto", label: "Auto", hint: "Follows the time of day" },
  { value: "day", label: "Light", hint: "Always light" },
  { value: "night", label: "Dark", hint: "Always dark" },
];

/** How the room looks and sounds. "Auto" lets the light follow your real day. */
export function Controls() {
  const { mode, setMode } = useLight();
  const { muted, setMuted } = useAcoustics();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p id="light-label" className="text-[length:var(--text-small)] text-ink-soft">
          Room light
        </p>
        <button
          onClick={() => setMuted(!muted)}
          aria-pressed={!muted}
          aria-label={muted ? "Soft sounds are off — turn on" : "Soft sounds are on — turn off"}
          title={muted ? "Soft sounds are off" : "Soft sounds are on"}
          className="grid size-9 place-items-center rounded-full text-ink-soft hover:bg-raised hover:text-ink"
        >
          {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
        </button>
      </div>
      <div role="radiogroup" aria-labelledby="light-label" className="flex gap-1 rounded-full bg-ground p-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            role="radio"
            aria-checked={mode === m.value}
            title={m.hint}
            onClick={() => setMode(m.value)}
            className={cn(
              "min-h-9 flex-1 rounded-full px-2 text-[length:var(--text-small)] transition-colors",
              mode === m.value ? "bg-raised text-ink" : "text-ink-soft hover:text-ink"
            )}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
