"use client";

import { useState } from "react";
import {
  CommandSurface,
  type CommandResult,
  type SearchKind,
} from "@/components/primitives/CommandSurface";
import { searchMemory, searchMessages } from "@/lib/api/client";
import { relativeTime } from "@/lib/time";

/**
 * The ⌘K search over the conversation. Keyword search jumps the thread to a message; semantic
 * search surfaces recalled memories. Results never render inside the thread itself.
 */
export function ChatSearch() {
  const [open, setOpen] = useState(false);

  const runSearch = async (kind: SearchKind, q: string): Promise<CommandResult[]> => {
    if (kind === "keyword") {
      const rows = await searchMessages(q, { limit: 12 });
      return rows.map((r) => ({
        id: r.message_id,
        title: r.content.replace(/\s+/g, " ").slice(0, 140),
        when: relativeTime(r.created_at),
      }));
    }
    const rows = await searchMemory(q, 8);
    return rows.map((r) => ({
      id: `mem-${r.memory_id}`,
      title: r.summary,
      when: relativeTime(r.created_at),
    }));
  };

  const onSelect = (r: CommandResult, kind: SearchKind) => {
    if (kind !== "keyword") return; // memories aren't messages — closing is enough for now
    const el = document.getElementById(`msg-${r.id}`);
    if (!el) return; // out of the loaded window (paging back to it is a later slice)
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.animate(
      [
        { boxShadow: "inset 0 0 0 9999px rgba(154,123,79,0.07)" },
        { boxShadow: "inset 0 0 0 9999px rgba(154,123,79,0)" },
      ],
      { duration: 1400, easing: "ease-out" }
    );
  };

  return (
    <CommandSurface
      open={open}
      onOpenChange={setOpen}
      runSearch={runSearch}
      onSelect={onSelect}
    />
  );
}
