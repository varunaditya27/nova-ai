"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { SavedMessage } from "@/components/vault/SavedMessage";
import { useAnnotate, useBookmarks } from "@/lib/hooks/useVault";

/** Saved messages — things worth keeping, pulled out of the thread. */
export default function Bookmarks() {
  const { data, isLoading } = useBookmarks();
  const { bookmark } = useAnnotate();

  return (
    <PageShell title="Kept" description="Messages you saved — a shelf pulled out of the conversation.">
      {isLoading && <div className="h-20 rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">Nothing saved yet. Hover a message in chat and keep it.</p>
      )}
      <div className="flex flex-col gap-3">
        {data?.map((m) => (
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
