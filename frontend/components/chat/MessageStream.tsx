"use client";

import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { ThreadLine } from "@/components/primitives/ThreadLine";
import { EchoRail } from "@/components/primitives/EchoRail";
import { VoiceButton } from "./VoiceButton";
import { relativeTime } from "@/lib/time";
import { springs, useReducedMotionSafe } from "@/lib/motion";
import type { MessageOut } from "@/lib/api/types";
import type { StreamState } from "@/lib/chat/streamReducer";

function Body({ content }: { content: string }) {
  return <div className="whitespace-pre-wrap">{content}</div>;
}

/** Three dots that breathe while Nova composes — a thinking pause, not a spinner. */
function Thinking() {
  const { reduced } = useReducedMotionSafe();
  return (
    <span className="inline-flex items-center gap-1 py-1" aria-label="Nova is thinking">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-ink-faint"
          animate={reduced ? undefined : { opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.18 }}
        />
      ))}
    </span>
  );
}

export function MessageStream({
  messages,
  pendingUser,
  streaming,
  hasOlder,
  loadingOlder,
  onLoadOlder,
}: {
  messages: MessageOut[];
  pendingUser: string | null;
  streaming: StreamState;
  hasOlder: boolean;
  loadingOlder: boolean;
  onLoadOlder: () => void;
}) {
  const { t } = useReducedMotionSafe();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Continue-from-bottom: keep the newest turn in view as the conversation grows.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, pendingUser, streaming.text, streaming.phase]);

  const showStreaming = streaming.phase === "streaming" || streaming.phase === "error";

  return (
    <div className="flex flex-col">
      {hasOlder && (
        <button
          onClick={onLoadOlder}
          disabled={loadingOlder}
          className="mx-auto mb-2 rounded-md px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint transition-colors hover:text-ink-soft"
        >
          {loadingOlder ? "gathering…" : "earlier"}
        </button>
      )}

      {messages.map((m) => (
        <div key={m.message_id} id={`msg-${m.message_id}`} className="scroll-mt-24">
          <ThreadLine role={m.role} timestamp={relativeTime(m.created_at)}>
            <Body content={m.content} />
            {m.role === "nova" && (
              <>
                <div className="mt-1 flex items-center">
                  <VoiceButton text={m.content} mode={m.conversation_mode ?? "casual"} />
                </div>
                {m.echoes.length > 0 && <EchoRail echoes={m.echoes} />}
              </>
            )}
          </ThreadLine>
        </div>
      ))}

      {pendingUser && (
        <ThreadLine role="user">
          <Body content={pendingUser} />
        </ThreadLine>
      )}

      {showStreaming && (
        <ThreadLine role="nova">
          {streaming.text ? <Body content={streaming.text} /> : <Thinking />}
          {streaming.phase === "error" && streaming.error && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={t(springs.wake)}
              className="mt-1 text-sm text-ink-soft"
            >
              {streaming.error}
            </motion.p>
          )}
        </ThreadLine>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
