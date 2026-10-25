"use client";

import { useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { HandHelping } from "lucide-react";
import { Ember } from "@/components/ui/Ember";
import { Button } from "@/components/ui/Button";
import { groupSittings } from "@/lib/chat/sittings";
import type { StreamState } from "@/lib/chat/streamReducer";
import type { MessageOut } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { Echoes } from "./Echoes";
import { MessageActions } from "./MessageActions";

function clock(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** Nova's name on a reply, sitting on the thread. */
function NovaMark({ thinking = false }: { thinking?: boolean }) {
  return (
    <span
      className="absolute left-0 top-0.5 grid size-7 place-items-center cut-sm bg-ground text-accent"
      aria-hidden
    >
      <Ember size={18} state={thinking ? "thinking" : "still"} />
    </span>
  );
}

function Row({
  message,
  speakingId,
  onSpeak,
}: {
  message: MessageOut;
  speakingId: string | null;
  onSpeak: (m: MessageOut) => void;
}) {
  const mine = message.role === "user";
  const crisis = !mine && message.crisis_active;

  if (mine) {
    return (
      <article
        id={`msg-${message.message_id}`}
        className="group scroll-mt-24 pl-10 sm:pl-14"
      >
        <div className="ml-auto w-fit max-w-[88%]">
          <p className="mb-1 text-right text-[length:var(--text-small)] text-mute">
            You{" "}
            <time className="opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
              · {clock(message.created_at)}
            </time>
          </p>
          <p className="read whitespace-pre-wrap">{message.content}</p>
          <MessageActions message={message} speaking={false} />
        </div>
      </article>
    );
  }

  return (
    <article
      id={`msg-${message.message_id}`}
      className="group relative scroll-mt-24 pl-10 sm:pl-14"
    >
      <NovaMark />
      <div className={cn(crisis && "tone-sunk px-6 py-5")}>
        <p className="mb-1 text-[length:var(--text-small)] text-mute">
          {crisis ? "Nova is staying with you" : "Nova"}{" "}
          <time className="opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
            · {clock(message.created_at)}
          </time>
        </p>
        <p className="read max-w-[62ch] whitespace-pre-wrap">
          {message.content}
        </p>
        {crisis && (
          <p className="mt-3 text-[length:var(--text-small)] text-ink-soft">
            If you want someone to talk to right now,{" "}
            <Link
              href="/care"
              className="text-accent underline underline-offset-4"
            >
              here are people you can call
            </Link>
            .
          </p>
        )}
        {message.tool_invoked && (
          <p className="mt-3 flex items-center gap-2 text-[length:var(--text-small)] text-ink-soft">
            <HandHelping size={15} aria-hidden /> Nova handled this as an errand
            —{" "}
            <Link
              href="/errands"
              className="text-accent underline underline-offset-4"
            >
              see Errands
            </Link>
          </p>
        )}
        <Echoes echoes={message.echoes} />
        <MessageActions
          message={message}
          speaking={speakingId === message.message_id}
          onSpeak={() => onSpeak(message)}
        />
      </div>
    </article>
  );
}

/**
 * The one permanent conversation, read top to bottom. Sittings are separated by a knot on the thread
 * and the day in words; long silences are named ("A week passes.") so time is visible, not hidden.
 */
export function Thread({
  messages,
  pendingUser,
  streaming,
  opening,
  onDismissOpening,
  hasOlder,
  loadingOlder,
  onLoadOlder,
  speakingId,
  onSpeak,
}: {
  messages: MessageOut[];
  pendingUser: string | null;
  streaming: StreamState;
  /** Something Nova wants to say first; shown at the end of the thread. */
  opening: string | null;
  onDismissOpening: () => void;
  hasOlder: boolean;
  loadingOlder: boolean;
  onLoadOlder: () => void;
  speakingId: string | null;
  onSpeak: (m: MessageOut) => void;
}) {
  const sittings = useMemo(() => groupSittings(messages), [messages]);
  const bottom = useRef<HTMLDivElement>(null);
  const showStreaming =
    streaming.phase === "streaming" || streaming.phase === "error";

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages.length, pendingUser, streaming.text, streaming.phase, opening]);

  return (
    <div className="relative">
      {/* The thread: one continuous line the whole conversation hangs on. */}
      <span
        aria-hidden
        className="absolute bottom-0 left-[13px] top-2 w-[3px] cut-sm bg-sunk"
      />

      {hasOlder && (
        <div className="relative pb-8 pl-10 sm:pl-14">
          <Button variant="quiet" onClick={onLoadOlder} disabled={loadingOlder}>
            {loadingOlder
              ? "Finding earlier conversations…"
              : "Show earlier conversations"}
          </Button>
        </div>
      )}

      <div className="flex flex-col gap-9">
        {sittings.map((s) => (
          <section
            key={s.key}
            aria-label={s.heading}
            className="flex flex-col gap-7"
          >
            {s.passage && (
              <p className="relative py-4 pl-10 italic text-mute sm:pl-14">
                <span
                  aria-hidden
                  className="absolute left-[6px] top-1/2 size-[10px] -translate-y-1/2 rounded-full bg-ground ring-[3px] ring-sunk"
                />
                {s.passage}
              </p>
            )}
            <h2 className="relative pl-10 font-body text-[length:var(--text-small)] font-normal tracking-normal text-ink-soft sm:pl-14">
              <span
                aria-hidden
                className="absolute left-[3px] top-1/2 size-4 -translate-y-1/2 rounded-full bg-accent"
              />
              {s.heading}
            </h2>
            {s.messages.map((m) => (
              <Row
                key={m.message_id}
                message={m}
                speakingId={speakingId}
                onSpeak={onSpeak}
              />
            ))}
          </section>
        ))}

        {pendingUser && (
          <article className="pl-10 sm:pl-14">
            <div className="ml-auto w-fit max-w-[88%]">
              <p className="mb-1 text-right text-[length:var(--text-small)] text-mute">
                You
              </p>
              <p className="read whitespace-pre-wrap">{pendingUser}</p>
            </div>
          </article>
        )}

        {showStreaming && (
          <article
            className="relative pl-10 sm:pl-14"
            aria-live="polite"
            aria-busy={streaming.phase === "streaming"}
          >
            <NovaMark thinking={!streaming.text} />
            <p className="mb-1 text-[length:var(--text-small)] text-mute">
              {streaming.text ? "Nova" : "Nova is thinking…"}
            </p>
            {streaming.text && (
              <p className="read max-w-[62ch] whitespace-pre-wrap">
                {streaming.text}
              </p>
            )}
            {streaming.phase === "error" && streaming.error && (
              <p className="mt-2 text-ink-soft">{streaming.error}</p>
            )}
          </article>
        )}

        {opening && !pendingUser && !showStreaming && (
          <article className="relative pl-10 sm:pl-14">
            <NovaMark />
            <p className="mb-1 text-[length:var(--text-small)] text-mute">
              Nova wanted to start this one
            </p>
            <p className="read max-w-[62ch] whitespace-pre-wrap">{opening}</p>
            <button
              onClick={onDismissOpening}
              className="mt-3 min-h-9 cut-sm bg-sunk px-4 text-[length:var(--text-small)] text-ink-soft hover:text-ink"
            >
              Not now
            </button>
          </article>
        )}
      </div>
      <div ref={bottom} className="h-2" />
    </div>
  );
}
