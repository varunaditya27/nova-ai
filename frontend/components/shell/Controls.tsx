"use client";

import { useLight, type LightMode } from "@/components/ThemeProvider";
import { cn } from "@/lib/cn";

const MODES: { value: LightMode; label: string; hint: string }[] = [
  { value: "auto", label: "Auto", hint: "Follows the time of day" },
  { value: "day", label: "Light", hint: "Always light" },
  { value: "night", label: "Dark", hint: "Always dark" },
];

/** How the room looks. "Auto" lets the light follow your real day. */
export function Controls() {
  const { mode, setMode } = useLight();
  return (
    <div className="flex flex-col gap-2">
      <p
        id="light-label"
        className="text-[length:var(--text-small)] text-ink-soft"
      >
        Room light
      </p>
      <div
        role="radiogroup"
        aria-labelledby="light-label"
        className="flex gap-1 bg-ground p-1"
      >
        {MODES.map((m) => (
          <button
            key={m.value}
            role="radio"
            aria-checked={mode === m.value}
            title={m.hint}
            onClick={() => setMode(m.value)}
            className={cn(
              "min-h-9 flex-1 px-2 text-[length:var(--text-small)] transition-colors",
              mode === m.value
                ? "bg-raised text-ink"
                : "text-ink-soft hover:text-ink",
            )}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
