"use client";

import { useId, type KeyboardEvent } from "react";
import { cn } from "@/lib/cn";

/** A segmented control: one flat tone track, the chosen option lifted a tone step. Arrow keys move. */
export function Tabs<T extends string>({
  value,
  onChange,
  items,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { value: T; label: string; count?: number }[];
  label: string;
}) {
  const id = useId();
  const move = (e: KeyboardEvent, index: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const next = (index + (e.key === "ArrowRight" ? 1 : -1) + items.length) % items.length;
    onChange(items[next].value);
    document.getElementById(`${id}-${items[next].value}`)?.focus();
  };

  return (
    <div role="tablist" aria-label={label} className="inline-flex max-w-full gap-1 overflow-x-auto rounded-full bg-sunk p-1">
      {items.map((item, i) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            id={`${id}-${item.value}`}
            role="tab"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(item.value)}
            onKeyDown={(e) => move(e, i)}
            className={cn(
              "min-h-10 shrink-0 rounded-full px-5 text-[length:var(--text-body)] transition-colors duration-200",
              active ? "bg-raised text-ink" : "text-ink-soft hover:text-ink"
            )}
          >
            {item.label}
            {item.count != null && item.count > 0 && (
              <span className="ml-2 text-[length:var(--text-small)] text-mute">{item.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
