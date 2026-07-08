"use client";

import { Surface } from "@/components/primitives/Surface";
import { relativeTime } from "@/lib/time";
import type { MessageOut } from "@/lib/api/types";

/** A saved message (bookmark or milestone) with a remove affordance. */
export function SavedMessage({
  message,
  tag,
  tagBrass = false,
  onRemove,
}: {
  message: MessageOut;
  tag?: string | null;
  tagBrass?: boolean;
  onRemove: () => void;
}) {
  return (
    <Surface className="p-5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-display text-sm text-ink-soft">
          {message.role === "nova" ? "Nova" : "You"}
        </span>
        <button
          onClick={onRemove}
          className="font-mono text-[10px] uppercase tracking-widest text-ink-faint transition-colors hover:text-ink-soft"
        >
          remove
        </button>
      </div>
      <p className="mt-1.5 text-[15px] leading-relaxed text-ink">{message.content}</p>
      <div className="mt-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
        {tag && <span style={tagBrass ? { color: "var(--brass)" } : undefined}>{tag}</span>}
        {tag && <span aria-hidden>·</span>}
        <span>{relativeTime(message.created_at)}</span>
      </div>
    </Surface>
  );
}
