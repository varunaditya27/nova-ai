"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Mic, Volume2, VolumeX } from "lucide-react";
import { useDictation } from "@/lib/hooks/useDictation";
import { partOfDay } from "@/lib/time";
import { cn } from "@/lib/cn";

function placeholderFor(now: Date): string {
  switch (partOfDay(now)) {
    case "morning":
      return "How’s your morning?";
    case "afternoon":
      return "What’s on your mind?";
    case "evening":
      return "How was your day?";
    default:
      return "Still up? Say it here.";
  }
}

/**
 * Where you talk. Enter sends, Shift+Enter adds a line, and the limits are written out rather than
 * discovered. Hold the mic to dictate; the words land in the box so you can fix them before sending.
 */
export function Composer({
  value,
  onChange,
  onSend,
  disabled,
  readAloud,
  onToggleReadAloud,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled: boolean;
  readAloud: boolean;
  onToggleReadAloud: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const dictation = useDictation((text) =>
    onChange(value ? `${value} ${text}` : text),
  );
  const canSend = !disabled && value.trim().length > 0;
  // The hour is only known in the browser; start neutral so server and client first paint agree.
  const [placeholder, setPlaceholder] = useState("What’s on your mind?");
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only time of day
    setPlaceholder(placeholderFor(new Date()));
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
    el.style.overflowY = el.scrollHeight > 220 ? "auto" : "hidden";
  }, [value]);

  return (
    <div className="flex flex-col gap-2">
      <div className="tone flex items-end gap-2 fold px-5 py-3">
        <label htmlFor="say" className="sr-only">
          Say something to Nova
        </label>
        <textarea
          id="say"
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
          placeholder={placeholder}
          aria-describedby="say-hint"
          className="read max-h-[220px] min-h-11 flex-1 resize-none overflow-y-hidden bg-transparent py-2 outline-none placeholder:text-mute"
        />
        {dictation.supported && (
          <button
            type="button"
            disabled={disabled}
            onPointerDown={dictation.start}
            onPointerUp={dictation.stop}
            onPointerLeave={dictation.stop}
            aria-label={
              dictation.recording
                ? "Listening — let go to finish"
                : "Hold to talk"
            }
            className={cn(
              "grid size-11 shrink-0 place-items-center transition-colors",
              dictation.recording
                ? "bg-accent text-accent-ink"
                : "bg-sunk text-ink hover:bg-raised",
            )}
          >
            <Mic
              size={18}
              className={dictation.transcribing ? "animate-pulse" : undefined}
            />
          </button>
        )}
        <button
          type="button"
          onClick={() => canSend && onSend()}
          disabled={!canSend}
          aria-label="Send"
          className={cn(
            "grid size-11 shrink-0 place-items-center fold-sm transition-colors",
            canSend
              ? "bg-accent text-accent-ink hover:brightness-110"
              : "bg-sunk text-mute",
          )}
        >
          <ArrowUp size={20} />
        </button>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-3">
        <p
          id="say-hint"
          className="text-[length:var(--text-small)] text-mute"
          role="status"
        >
          {dictation.recording
            ? "Listening… let go when you’re done."
            : dictation.transcribing
              ? "Writing down what you said…"
              : (dictation.error ?? "Enter sends · Shift+Enter for a new line")}
        </p>
        <button
          onClick={onToggleReadAloud}
          aria-pressed={readAloud}
          className="inline-flex min-h-9 items-center gap-2 px-2 text-[length:var(--text-small)] text-ink-soft hover:text-ink"
        >
          {readAloud ? (
            <Volume2 size={15} aria-hidden />
          ) : (
            <VolumeX size={15} aria-hidden />
          )}
          {readAloud ? "I’ll read replies aloud" : "Read replies aloud"}
        </button>
      </div>
    </div>
  );
}
