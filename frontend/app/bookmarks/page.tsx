"use client";

import { useState } from "react";
import { PageShell } from "@/components/primitives/PageShell";
import { SavedMessage } from "@/components/vault/SavedMessage";
import { useAnnotate, useBookmarks } from "@/lib/hooks/useVault";
import { cn } from "@/lib/cn";

/** Saved messages — things worth keeping, filterable by the category you filed them under. */
export default function Bookmarks() {
  const { data, isLoading } = useBookmarks();
  const { bookmark } = useAnnotate();
  const [category, setCategory] = useState<string | null>(null);

  const categories = [
    ...new Set((data ?? []).map((m) => m.bookmark_category).filter(Boolean) as string[]),
  ];
  const shown = category ? (data ?? []).filter((m) => m.bookmark_category === category) : data;

  return (
    <PageShell title="Kept" description="Messages you saved — a shelf pulled out of the conversation.">
      {categories.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-1.5">
          {[null, ...categories].map((c) => (
            <button
              key={c ?? "all"}
              onClick={() => setCategory(c)}
              className={cn(
                "rounded-sm border px-2.5 py-1 text-[11px] uppercase tracking-widest transition-colors",
                category === c
                  ? "border-hairline bg-surface text-ink"
                  : "border-transparent text-ink-faint hover:text-ink-soft"
              )}
            >
              {c ?? "all"}
            </button>
          ))}
        </div>
      )}

      {isLoading && <div className="h-20 rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">Nothing saved yet. Hover a message in chat and keep it.</p>
      )}
      <div className="flex flex-col gap-3">
        {shown?.map((m) => (
          <SavedMessage
            key={m.message_id}
            message={m}
            tag={m.bookmark_category}
            onRemove={() => bookmark.mutate({ id: m.message_id, on: false })}
          />
        ))}
      </div>
    </PageShell>
  );
}
