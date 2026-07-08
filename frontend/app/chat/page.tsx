"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useMessages } from "@/lib/hooks/useMessages";
import { useChatStream } from "@/lib/hooks/useChatStream";
import { MessageStream } from "@/components/chat/MessageStream";
import { Composer } from "@/components/chat/Composer";
import { ChatSearch } from "@/components/chat/ChatSearch";

/**
 * The Conversation — the sacred space. One permanent thread loaded from history, new turns streamed
 * in, echoes surfaced from the persisted turn after it lands. Search lives only in ⌘K, never here.
 */
export default function Chat() {
  const qc = useQueryClient();
  const { messages, isLoading, hasNextPage, isFetchingNextPage, fetchNextPage } = useMessages();
  const stream = useChatStream();

  const [value, setValue] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();

  const streaming = stream.state.phase === "streaming";

  const onSend = async () => {
    const text = value.trim();
    if (!text || streaming) return;
    setValue("");
    setPending(text);

    const result = await stream.send(text, sessionId);
    if (result.sessionId) setSessionId(result.sessionId);

    if (result.phase === "error") return; // leave the turn + error visible for a retry

    // The streamed reply carries no echoes; refetch so the persisted turn (with its echoes) lands,
    // then drop the optimistic overlays.
    await qc.invalidateQueries({ queryKey: ["messages"] });
    setPending(null);
    stream.reset();
  };

  const empty =
    !isLoading && messages.length === 0 && !pending && stream.state.phase === "idle";

  return (
    <main className="relative z-10 mx-auto flex min-h-dvh max-w-2xl flex-col px-6 pb-48 pt-16 sm:px-10">
      <div className="flex-1">
        {empty ? (
          <div className="flex min-h-[55vh] flex-col justify-center">
            <p
              className="max-w-md font-display text-2xl leading-snug text-ink"
              style={{ fontVariationSettings: '"opsz" 60, "SOFT" 30, "wght" 400' }}
            >
              Nothing yet. Say the first thing — Nova will remember it.
            </p>
          </div>
        ) : (
          <MessageStream
            messages={messages}
            pendingUser={pending}
            streaming={stream.state}
            hasOlder={Boolean(hasNextPage)}
            loadingOlder={isFetchingNextPage}
            onLoadOlder={() => fetchNextPage()}
          />
        )}
      </div>

      {/* A paper fade so the thread dissolves into the page under the composer, never hard-cut. */}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-20 h-52 bg-gradient-to-t from-paper from-40% to-transparent" />

      {/* The composer floats above the dock, centered on the same column as the thread. */}
      <div className="fixed inset-x-0 bottom-24 z-30">
        <div className="mx-auto max-w-2xl px-6 sm:px-10">
          <Composer value={value} onChange={setValue} onSend={onSend} disabled={streaming} />
        </div>
      </div>

      <ChatSearch />
    </main>
  );
}
