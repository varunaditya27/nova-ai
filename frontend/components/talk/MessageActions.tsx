"use client";

import { useState } from "react";
import { Bookmark, Copy, Star, Volume2, VolumeX } from "lucide-react";
import { useAnnotate } from "@/lib/hooks/useVault";
import { useToast } from "@/lib/hooks/useToast";
import { useAcoustics } from "@/lib/hooks/useAcoustics";
import { cn } from "@/lib/cn";
import type { MessageOut } from "@/lib/api/types";

const CATEGORIES = ["Advice", "Funny", "Hard days", "Ideas"];

const chip =
  "inline-flex min-h-9 items-center gap-1.5 rounded-full px-3.5 text-[length:var(--text-small)] text-ink-soft transition-colors hover:bg-sunk hover:text-ink";

/**
 * What you can do with one message: keep it, mark it as a moment that mattered, copy it, hear it.
 * Hidden until you hover or focus (always shown on touch) so the thread stays a conversation.
 */
export function MessageActions({
  message,
  speaking,
  onSpeak,
}: {
  message: MessageOut;
  speaking: boolean;
  onSpeak?: () => void;
}) {
  const { bookmark, milestone } = useAnnotate();
  const { toast } = useToast();
  const { play } = useAcoustics();
  const [panel, setPanel] = useState<null | "save" | "moment">(null);
  const [custom, setCustom] = useState("");
  const [label, setLabel] = useState("");

  const keep = (category?: string) => {
    bookmark.mutate(
      { id: message.message_id, on: true, category },
      { onSuccess: () => toast("Saved to Keepsakes", category ? `Filed under “${category}”.` : undefined) }
    );
    play("click");
    setPanel(null);
    setCustom("");
  };
  const mark = () => {
    milestone.mutate(
      { id: message.message_id, on: true, label: label.trim() || undefined },
      { onSuccess: () => toast("Kept as a moment that mattered", "You’ll find it in Keepsakes.") }
    );
    play("click");
    setPanel(null);
    setLabel("");
  };

  return (
    <div className="mt-2">
      <div
        className={cn(
          "flex flex-wrap items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 [@media(hover:none)]:opacity-100",
          panel && "opacity-100"
        )}
      >
        {message.bookmarked ? (
          <button className={chip} onClick={() => bookmark.mutate({ id: message.message_id, on: false })}>
            <Bookmark size={15} className="fill-accent text-accent" aria-hidden />
            Saved{message.bookmark_category ? ` · ${message.bookmark_category}` : ""} — remove
          </button>
        ) : (
          <button className={chip} onClick={() => setPanel(panel === "save" ? null : "save")} aria-expanded={panel === "save"}>
            <Bookmark size={15} aria-hidden /> Save
          </button>
        )}
        {message.is_milestone ? (
          <button className={chip} onClick={() => milestone.mutate({ id: message.message_id, on: false })}>
            <Star size={15} className="fill-earned text-earned" aria-hidden />
            A moment that mattered{message.milestone_label ? ` · ${message.milestone_label}` : ""} — remove
          </button>
        ) : (
          <button className={chip} onClick={() => setPanel(panel === "moment" ? null : "moment")} aria-expanded={panel === "moment"}>
            <Star size={15} aria-hidden /> This mattered
          </button>
        )}
        {message.role === "nova" && onSpeak && (
          <button className={chip} onClick={onSpeak}>
            {speaking ? <VolumeX size={15} aria-hidden /> : <Volume2 size={15} aria-hidden />}
            {speaking ? "Stop" : "Hear it"}
          </button>
        )}
        <button
          className={chip}
          onClick={() => {
            navigator.clipboard?.writeText(message.content).then(() => toast("Copied"));
          }}
        >
          <Copy size={15} aria-hidden /> Copy
        </button>
      </div>

      {panel === "save" && (
        <div className="tone mt-2 flex flex-wrap items-center gap-2 px-4 py-3">
          <span className="text-[length:var(--text-small)] text-ink-soft">File it under</span>
          {CATEGORIES.map((c) => (
            <button key={c} onClick={() => keep(c)} className="min-h-9 rounded-full bg-sunk px-4 text-[length:var(--text-small)] hover:bg-raised">
              {c}
            </button>
          ))}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (custom.trim()) keep(custom.trim());
            }}
            className="flex items-center gap-2"
          >
            <input
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              aria-label="Your own name for this folder"
              placeholder="or your own…"
              className="min-h-9 w-36 rounded-full bg-sunk px-4 text-[length:var(--text-small)] outline-none placeholder:text-mute"
            />
          </form>
          <button onClick={() => keep()} className="min-h-9 px-2 text-[length:var(--text-small)] text-accent underline underline-offset-4">
            No folder
          </button>
        </div>
      )}

      {panel === "moment" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mark();
          }}
          className="tone mt-2 flex flex-wrap items-center gap-3 px-4 py-3"
        >
          <label className="text-[length:var(--text-small)] text-ink-soft" htmlFor={`moment-${message.message_id}`}>
            What should this moment be called?
          </label>
          <input
            id={`moment-${message.message_id}`}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. Got into RVCE"
            className="min-h-9 min-w-48 flex-1 rounded-full bg-sunk px-4 text-[length:var(--text-small)] outline-none placeholder:text-mute"
          />
          <button type="submit" className="min-h-9 rounded-full bg-accent px-5 text-[length:var(--text-small)] text-accent-ink">
            Keep it
          </button>
        </form>
      )}
    </div>
  );
}
