"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  CommandSurface,
  type CommandResult,
  type SearchKind,
} from "@/components/primitives/CommandSurface";
import { searchMemory, searchMessages } from "@/lib/api/client";
import { relativeTime } from "@/lib/time";

/**
 * The ⌘K search over the conversation. A keyword hit is handed back to the thread via `onJump`
 * (which pages back until the message is loaded, then scrolls to it); a semantic hit opens the
 * matching memory in the vault. Results never render inside the thread itself.
 */
export function ChatSearch({ onJump }: { onJump: (messageId: string) => void }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();

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
    if (kind === "keyword") onJump(r.id);
    else router.push(`/memories#${r.id}`); // r.id is `mem-<memory_id>`
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
