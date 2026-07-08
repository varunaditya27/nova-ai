"use client";

import { Award, Bookmark } from "lucide-react";
import { cn } from "@/lib/cn";
import { useAnnotate } from "@/lib/hooks/useVault";
import type { MessageOut } from "@/lib/api/types";

/** Bookmark / milestone toggles that appear on hover. Set state reads brass (earned). */
export function MessageActions({ message }: { message: MessageOut }) {
  const { bookmark, milestone } = useAnnotate();
  const btn = (on: boolean) =>
    cn(
      "rounded-sm p-1 transition-opacity",
      on
        ? "text-brass opacity-100"
        : "text-ink-faint opacity-0 hover:text-ink-soft group-hover:opacity-100"
    );

  return (
    <>
      <button
        onClick={() => bookmark.mutate({ id: message.message_id, on: !message.bookmarked })}
        aria-label={message.bookmarked ? "Remove bookmark" : "Save message"}
        className={btn(message.bookmarked)}
      >
        <Bookmark size={13} fill={message.bookmarked ? "currentColor" : "none"} />
      </button>
      <button
        onClick={() => milestone.mutate({ id: message.message_id, on: !message.is_milestone })}
        aria-label={message.is_milestone ? "Remove milestone" : "Mark as milestone"}
        className={btn(message.is_milestone)}
      >
        <Award size={13} fill={message.is_milestone ? "currentColor" : "none"} />
      </button>
    </>
  );
}
