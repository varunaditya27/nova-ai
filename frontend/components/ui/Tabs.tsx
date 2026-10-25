"use client";

import { useId, type KeyboardEvent } from "react";
import { cn } from "@/lib/cn";

/** A segmented control: plain rectangles on one rule, the chosen one underlined in accent. Arrow keys move. */
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
    const next =
      (index + (e.key === "ArrowRight" ? 1 : -1) + items.length) % items.length;
    onChange(items[next].value);
    document.getElementById(`${id}-${items[next].value}`)?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label={label}
      className="inline-flex max-w-full overflow-x-auto shadow-[inset_0_-1px_0_var(--rule)]"
    >
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
              "relative min-h-12 shrink-0 px-5 text-[length:var(--text-body)] transition-colors duration-300 focus-visible:outline-offset-[-5px]",
              active ? "text-ink" : "text-ink-soft hover:text-ink",
            )}
          >
            {item.label}
            {item.count != null && item.count > 0 && (
              <span className="ml-2 text-[length:var(--text-small)] text-mute">
                {item.count}
              </span>
            )}
            <span
              aria-hidden
              className={cn(
                "absolute inset-x-5 bottom-0 h-[3px] origin-left bg-accent transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
                active ? "scale-x-100" : "scale-x-0",
              )}
            />
          </button>
        );
      })}
    </div>
  );
}
