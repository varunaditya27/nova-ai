"use client";

import { cn } from "@/lib/cn";

/** A flat progress track: sunk tone, accent fill. `earned` swaps in marigold for finished things. */
export function Meter({
  value,
  earned = false,
  label,
  className,
}: {
  value: number;
  earned?: boolean;
  label: string;
  className?: string;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      className={cn("ruler h-3 w-full overflow-hidden bg-sunk", className)}
    >
      <div
        className={cn(
          "h-full transition-[width] duration-700",
          earned ? "bg-earned" : "bg-accent",
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

const TONES = [
  "bg-accent text-accent-ink",
  "bg-earned text-accent-ink",
  "bg-ink text-ground",
  "bg-sunk text-ink",
] as const;

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

/** Initials on a flat tone chosen from the name, so the same person always looks the same. */
export function Avatar({
  name,
  size = 48,
  className,
}: {
  name: string;
  size?: number;
  className?: string;
}) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
  return (
    <span
      aria-hidden
      className={cn(
        "grid shrink-0 place-items-center fold-sm font-display",
        TONES[hash(name) % TONES.length],
        className,
      )}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
    >
      {initials || "?"}
    </span>
  );
}
