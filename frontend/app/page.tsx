"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { Composer } from "@/components/talk/Composer";
import { Thread } from "@/components/talk/Thread";
import { PendingCard } from "@/components/errands/PendingCard";
import { useCommandMenu } from "@/components/shell/CommandMenu";
import { Skeleton } from "@/components/ui/States";
import { markProactiveDelivered } from "@/lib/api/client";
import { TypingTracker } from "@/lib/chat/typingSignals";
import { useChatStream } from "@/lib/hooks/useChatStream";
import { useHome } from "@/lib/hooks/useHome";
import { useMessages } from "@/lib/hooks/useMessages";
import { useProactiveStream } from "@/lib/hooks/useProactiveStream";
import { useProactive } from "@/lib/hooks/useNovaState";
import { usePendingTools } from "@/lib/hooks/useTools";
import { useVoice } from "@/lib/hooks/useVoice";
import { useReducedMotionSafe } from "@/lib/motion";
import { mergeProactiveItems } from "@/lib/proactive/merge";
import type { MessageOut } from "@/lib/api/types";

const STARTERS = [
  "Let me tell you about my week.",
  "There’s something I’m working toward.",
  "I’ve had something on my mind lately.",
];

function Talk() {
  const qc = useQueryClient();
  const router = useRouter();
  const params = useSearchParams();
  const menu = useCommandMenu();
  const { reduced } = useReducedMotionSafe();
  const home = useHome();
  const {
    messages,
    isLoading,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useMessages();
  const stream = useChatStream();
  const voice = useVoice();
  const errands = usePendingTools().data ?? [];
  const polled = useProactive().data;
  const live = useProactiveStream();

  const typing = useRef(new TypingTracker());
  const [value, setValue] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [readAloud, setReadAloud] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const streaming = stream.state.phase === "streaming";

  // Nova's cursor turns into handwriting while a reply is being written.
  useEffect(() => {
    const root = document.documentElement;
    if (streaming) root.dataset.busy = "true";
    else delete root.dataset.busy;
    return () => {
      delete root.dataset.busy;
    };
  }, [streaming]);

  // First visit ever: the front door comes first.
  useEffect(() => {
    if (!home.data || home.data.message_count > 0) return;
    try {
      if (!localStorage.getItem("nova-welcomed")) router.replace("/welcome");
    } catch {
      /* private mode: stay here */
    }
  }, [home.data, router]);

  useEffect(() => {
    try {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time client-only preference read
      setReadAloud(localStorage.getItem("nova-read-aloud") === "true");
    } catch {
      /* ignore */
    }
  }, []);
  const toggleReadAloud = () =>
    setReadAloud((v) => {
      try {
        localStorage.setItem("nova-read-aloud", String(!v));
      } catch {
        /* ignore */
      }
      return !v;
    });

  // Nova speaks first, when it has something worth saying: a live push, else what's queued.
  const openingItem =
    mergeProactiveItems(polled ?? [], live).find(
      (i) => !dismissed.includes(i.item_id),
    ) ?? null;
  const openingId = openingItem?.item_id;
  useEffect(() => {
    if (openingId) markProactiveDelivered(openingId).catch(() => undefined);
  }, [openingId]);

  const onSend = async () => {
    const text = value.trim();
    if (!text || streaming) return;
    const signals = {
      ...typing.current.snapshot(text),
      ...(openingItem ? { is_reply_to_proactive: true } : {}),
    };
    if (openingItem) setDismissed((d) => [...d, openingItem.item_id]);
    setValue("");
    setPending(text);

    const result = await stream.send(text, sessionId, signals);
    if (result.sessionId) setSessionId(result.sessionId);
    if (result.phase === "error") return; // leave the turn and the plain-language error visible

    if (readAloud && result.text)
      voice.speak(result.text, result.meta?.conversation_mode ?? "casual");

    // The stream carries no echoes or ids; refetch so the persisted turn lands, then drop overlays.
    await qc.invalidateQueries({ queryKey: ["messages"] });
    qc.invalidateQueries({ queryKey: ["tools"] });
    qc.invalidateQueries({ queryKey: ["goals"] });
    setPending(null);
    stream.reset();
  };

  const onSpeak = (m: MessageOut) => {
    if (speakingId === m.message_id && voice.playing) {
      voice.stop();
      setSpeakingId(null);
    } else {
      setSpeakingId(m.message_id);
      voice.speak(m.content, m.conversation_mode ?? "casual");
    }
  };
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reflect that playback ended
    if (!voice.playing) setSpeakingId(null);
  }, [voice.playing]);

  // Jump to a message (from search): page back until it is loaded, scroll to it, and let it glow once.
  const target = params.get("m");
  const jumped = useRef<string | null>(null);
  const jump = useCallback(
    async (id: string) => {
      for (let i = 0; i < 30; i++) {
        const el = document.getElementById(`msg-${id}`);
        if (el) {
          el.scrollIntoView({
            behavior: reduced ? "auto" : "smooth",
            block: "center",
          });
          if (!reduced)
            el.animate(
              [
                { backgroundColor: "var(--sunk)" },
                { backgroundColor: "transparent" },
              ],
              { duration: 2200 },
            );
          return;
        }
        if (!hasNextPage) return;
        await fetchNextPage();
        await new Promise((r) => setTimeout(r, 60));
      }
    },
    [hasNextPage, fetchNextPage, reduced],
  );
  useEffect(() => {
    if (!target || jumped.current === target || messages.length === 0) return;
    jumped.current = target;
    jump(target).then(() => router.replace("/", { scroll: false }));
  }, [target, messages.length, jump, router]);

  const empty =
    !isLoading &&
    messages.length === 0 &&
    !pending &&
    stream.state.phase === "idle";

  return (
    <div className="relative mx-auto flex min-h-dvh w-full max-w-3xl flex-col px-5 sm:px-8">
      <button
        onClick={menu.open}
        aria-label="Search the conversation"
        className="absolute right-5 top-5 z-10 grid size-11 place-items-center fold-sm bg-sunk text-ink-soft hover:text-ink sm:right-8"
      >
        <Search size={18} />
      </button>

      <div className="flex-1 pb-8 pt-20">
        {!empty && <h1 className="sr-only">Your conversation with Nova</h1>}
        {isLoading ? (
          <Skeleton lines={4} className="pl-14" />
        ) : empty ? (
          <div className="flex min-h-[48vh] flex-col justify-center gap-6">
            <h1 className="text-[length:var(--text-display)]">
              Say the first thing.
            </h1>
            <p className="read max-w-xl text-ink-soft">
              Nova remembers what you share, and builds on it over the weeks and
              years. There’s no wrong way to begin — or pick one of these.
            </p>
            <ul className="flex flex-col items-start gap-2">
              {STARTERS.map((s) => (
                <li key={s}>
                  <button
                    onClick={() => setValue(s)}
                    className="read min-h-11 fold-sm bg-sunk px-6 text-left hover:bg-raised"
                  >
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <Thread
            messages={messages}
            pendingUser={pending}
            streaming={stream.state}
            opening={openingItem?.message ?? null}
            onDismissOpening={() =>
              openingItem && setDismissed((d) => [...d, openingItem.item_id])
            }
            hasOlder={Boolean(hasNextPage)}
            loadingOlder={isFetchingNextPage}
            onLoadOlder={() => fetchNextPage()}
            speakingId={speakingId}
            onSpeak={onSpeak}
          />
        )}
      </div>

      <div className="sticky bottom-[4.75rem] z-10 flex flex-col gap-3 bg-ground pb-4 pt-3 lg:bottom-0">
        {errands.map((e) => (
          <PendingCard key={e.request_id} item={e} />
        ))}
        <Composer
          value={value}
          onChange={(v) => {
            typing.current.change(v);
            setValue(v);
          }}
          onSend={onSend}
          disabled={streaming}
          readAloud={readAloud}
          onToggleReadAloud={toggleReadAloud}
        />
      </div>
    </div>
  );
}

export default function TalkPage() {
  return (
    <Suspense fallback={null}>
      <Talk />
    </Suspense>
  );
}
