"use client";

import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Search, Volume2, VolumeX } from "lucide-react";
import { useMessages } from "@/lib/hooks/useMessages";
import { useChatStream } from "@/lib/hooks/useChatStream";
import { useVoice } from "@/lib/hooks/useVoice";
import { MessageStream } from "@/components/chat/MessageStream";
import { Composer } from "@/components/chat/Composer";
import { ChatSearch } from "@/components/chat/ChatSearch";
import { PendingActions } from "@/components/chat/PendingActions";
import { cn } from "@/lib/cn";

/**
 * The Conversation — the sacred space. One permanent thread loaded from history, new turns streamed
 * in, echoes surfaced from the persisted turn after it lands. Search lives only in ⌘K, never here.
 */
export default function Chat() {
  const qc = useQueryClient();
  const { messages, isLoading, hasNextPage, isFetchingNextPage, fetchNextPage } = useMessages();
  const stream = useChatStream();

  const voice = useVoice();
  const [value, setValue] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time client-only preference read
    setAutoSpeak(localStorage.getItem("nova-autospeak") === "true");
  }, []);
  const toggleAutoSpeak = () =>
    setAutoSpeak((v) => {
      const next = !v;
      try {
        localStorage.setItem("nova-autospeak", String(next));
      } catch {
        /* ignore */
      }
      return next;
    });

  const streaming = stream.state.phase === "streaming";

  const onSend = async () => {
    const text = value.trim();
    if (!text || streaming) return;
    setValue("");
    setPending(text);

    const result = await stream.send(text, sessionId);
    if (result.sessionId) setSessionId(result.sessionId);

    if (result.phase === "error") return; // leave the turn + error visible for a retry

    if (autoSpeak && result.text) {
      voice.speak(result.text, result.meta?.conversation_mode ?? "casual");
    }

    // The streamed reply carries no echoes; refetch so the persisted turn (with its echoes) lands,
    // then drop the optimistic overlays. Also refresh pending tools — a turn may have registered one.
    await qc.invalidateQueries({ queryKey: ["messages"] });
    qc.invalidateQueries({ queryKey: ["tools"] });
    setPending(null);
    stream.reset();
  };

  // Page back until the target message is loaded, then scroll to it and flash a brass wash.
  const jumpToMessage = useCallback(
    async (messageId: string) => {
      for (let i = 0; i < 30; i++) {
        const el = document.getElementById(`msg-${messageId}`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.animate(
            [
              { boxShadow: "inset 0 0 0 9999px rgba(154,123,79,0.07)" },
              { boxShadow: "inset 0 0 0 9999px rgba(154,123,79,0)" },
            ],
            { duration: 1400, easing: "ease-out" }
          );
          return;
        }
        if (!hasNextPage) return;
        await fetchNextPage();
        await new Promise((r) => setTimeout(r, 60)); // let the render commit
      }
    },
    [hasNextPage, fetchNextPage]
  );

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
          <PendingActions />
          <div className="mb-1.5 flex items-center justify-between">
            <button
              onClick={() => setSearchOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-sm px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-ink-faint transition-colors hover:text-ink-soft"
            >
              <Search size={12} />
              search <span className="hidden sm:inline">· ⌘K</span>
            </button>
            <button
              onClick={toggleAutoSpeak}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-sm px-2 py-1 font-mono text-[10px] uppercase tracking-widest transition-colors",
                autoSpeak ? "text-brass" : "text-ink-faint hover:text-ink-soft"
              )}
            >
              {autoSpeak ? <Volume2 size={12} /> : <VolumeX size={12} />}
              auto-speak
            </button>
          </div>
          <Composer value={value} onChange={setValue} onSend={onSend} disabled={streaming} />
        </div>
      </div>

      <ChatSearch open={searchOpen} onOpenChange={setSearchOpen} onJump={jumpToMessage} />
    </main>
  );
}
