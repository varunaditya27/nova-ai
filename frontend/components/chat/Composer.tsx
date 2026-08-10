"use client";

import { useEffect, useRef } from "react";
import { ArrowUp, Mic } from "lucide-react";
import { cn } from "@/lib/cn";
import { useDictation } from "@/lib/hooks/useDictation";

/**
 * The one input. A quiet auto-growing field — Enter sends, Shift+Enter makes a new line. Disabled
 * while a turn is in flight so the sacred one-thread order can't be raced.
 */
export function Composer({
  value,
  onChange,
  onSend,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const canSend = !disabled && value.trim().length > 0;
  const dictation = useDictation((text) => onChange(value ? `${value} ${text}` : text));

  return (
    <div
      className="flex items-end gap-2 rounded-lg border border-hairline bg-surface px-3 py-2"
      style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
    >
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (canSend) onSend();
          }
        }}
        rows={1}
        placeholder="Say something to Nova…"
        className="max-h-[200px] flex-1 resize-none bg-transparent py-1.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-ink-faint"
      />
      {dictation.supported && (
        <button
          type="button"
          disabled={disabled}
          onMouseDown={dictation.start}
          onMouseUp={dictation.stop}
          onMouseLeave={dictation.stop}
          onTouchStart={dictation.start}
          onTouchEnd={dictation.stop}
          aria-label="Hold to talk"
          className={cn(
            "mb-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition-colors",
            dictation.recording
              ? "border-brass/40 bg-brass/10 text-brass"
              : "border-hairline/50 text-ink-faint hover:text-ink-soft"
          )}
        >
          <Mic size={15} className={dictation.transcribing ? "animate-pulse" : ""} />
        </button>
      )}
      <button
        onClick={() => canSend && onSend()}
        disabled={!canSend}
        aria-label="Send"
        className={cn(
          "mb-0.5 inline-flex h-8 w-8 items-center justify-center rounded-md border transition-colors",
          canSend
            ? "border-hairline bg-raised text-ink hover:bg-paper"
            : "border-hairline/50 text-ink-faint"
        )}
      >
        <ArrowUp size={16} />
      </button>
    </div>
  );
}
