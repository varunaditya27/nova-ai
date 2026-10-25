"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { MemorySheet } from "@/components/memory/MemorySheet";
import { Page } from "@/components/ui/Page";
import { Tabs } from "@/components/ui/Tabs";
import { Empty, Skeleton, Trouble } from "@/components/ui/States";
import { searchMemory } from "@/lib/api/client";
import { useIntegrity, useMemoryAudit } from "@/lib/hooks/useVault";
import { relativeTime } from "@/lib/time";
import type { MemoryOut } from "@/lib/api/types";

type Tab = "events" | "learned";

/** How sure Nova is of something it has learned, in words. */
function sureness(confidence: number): string {
  if (confidence >= 0.8) return "Nova is quite sure";
  if (confidence >= 0.5) return "Nova thinks so";
  return "Nova is guessing";
}

function Entry({ m, onOpen }: { m: MemoryOut; onOpen: (id: string) => void }) {
  return (
    <li className="rule-top">
      <button
        onClick={() => onOpen(m.memory_id)}
        className="group block w-full px-5 py-4 text-left transition-colors hover:bg-surface"
      >
        <p className="read">{m.summary}</p>
        <p className="mt-1 text-[length:var(--text-small)] text-ink-soft">
          {relativeTime(m.created_at)}
          {m.topic_tags.length > 0
            ? ` · ${m.topic_tags.slice(0, 3).join(", ")}`
            : ""}
        </p>
      </button>
    </li>
  );
}

function Integrity() {
  const q = useIntegrity();
  if (q.isLoading || !q.data) return null;
  const ok = q.data.status === "INTACT";
  return (
    <p role="status" className="mt-16 max-w-2xl text-ink-soft">
      {ok
        ? "Nothing here has been changed since Nova wrote it. "
        : "Something in these records doesn’t add up — it may have been changed outside Nova. See Privacy for details. "}
      <button
        onClick={() => q.refetch()}
        className="text-accent underline underline-offset-4"
      >
        Check again
      </button>
    </p>
  );
}

function Ask({ onOpen }: { onOpen: (id: string) => void }) {
  const [text, setText] = useState("");
  const [asked, setAsked] = useState("");
  const q = useQuery({
    queryKey: ["ask", asked],
    queryFn: () => searchMemory(asked, 6),
    enabled: asked.length > 0,
  });
  return (
    <section aria-labelledby="ask" className="mb-12">
      <h2
        id="ask"
        className="rule-top pt-4 mb-3 text-[length:var(--text-read)]"
      >
        Ask Nova what it remembers
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setAsked(text.trim());
        }}
        className="tone flex items-center gap-3 fold-sm px-5 py-2"
      >
        <Search size={18} aria-hidden className="text-ink-soft" />
        <label htmlFor="ask-input" className="sr-only">
          Describe a moment or topic
        </label>
        <input
          id="ask-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Try “the time I was scared” or “my exam”"
          className="min-h-11 flex-1 bg-transparent outline-none placeholder:text-mute"
        />
        <button
          type="submit"
          disabled={!text.trim()}
          className="min-h-11 fold-sm bg-accent px-6 text-accent-ink disabled:opacity-50"
        >
          Ask
        </button>
      </form>
      {asked && (
        <div className="mt-5">
          {q.isLoading ? (
            <Skeleton lines={2} />
          ) : q.isError ? (
            <Trouble
              what="Nova couldn’t search its memory just now."
              onRetry={() => q.refetch()}
            />
          ) : (q.data ?? []).length === 0 ? (
            <p className="text-ink-soft">
              Nothing close to “{asked}”. Try describing it differently — memory
              is searched by meaning, not exact words.
            </p>
          ) : (
            <ul className="flex flex-col">
              {q.data?.map((m) => (
                <Entry key={m.memory_id} m={m} onOpen={onOpen} />
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function MemoryPage() {
  const router = useRouter();
  const params = useSearchParams();
  const audit = useMemoryAudit();
  const [tab, setTab] = useState<Tab>("events");
  const open = params.get("open");
  const setOpen = (id: string | null) =>
    router.replace(id ? `/memory?open=${id}` : "/memory", { scroll: false });

  const events = audit.data?.episodic ?? [];
  const learned = audit.data?.semantic ?? [];

  return (
    <Page
      title="Memory"
      intro="What Nova remembers, in its own words. Open a memory to read it in full or to make Nova forget it."
      actions={
        <Tabs
          label="Kind of memory"
          value={tab}
          onChange={setTab}
          items={[
            {
              value: "events",
              label: "Things that happened",
              count: events.length,
            },
            {
              value: "learned",
              label: "What Nova has learned",
              count: learned.length,
            },
          ]}
        />
      }
    >
      <Ask onOpen={setOpen} />
      {audit.isLoading ? (
        <Skeleton lines={4} />
      ) : audit.isError ? (
        <Trouble
          what="Nova’s memory couldn’t be read just now."
          onRetry={() => audit.refetch()}
        />
      ) : tab === "events" ? (
        events.length === 0 ? (
          <Empty title="Nothing remembered yet.">
            Nova doesn’t keep every word. It keeps what seems to matter — big
            feelings, big news, things about your life. They’ll appear here as
            you talk.
          </Empty>
        ) : (
          <ul className="flex max-w-3xl flex-col">
            {events.map((m) => (
              <Entry key={m.memory_id} m={m} onOpen={setOpen} />
            ))}
          </ul>
        )
      ) : learned.length === 0 ? (
        <Empty title="Nothing learned yet.">
          After enough conversations, Nova notices what stays true about you —
          what you like, how you work, who matters — and writes it down here.
        </Empty>
      ) : (
        <ul className="flex max-w-3xl flex-col gap-6">
          {learned.map((s) => (
            <li key={s.memory_id} className="rule-top pt-5">
              <p className="read">{s.statement}</p>
              <p className="text-[length:var(--text-small)] text-ink-soft">
                {sureness(s.confidence)}
              </p>
            </li>
          ))}
        </ul>
      )}
      <Integrity />
      <MemorySheet id={open} onClose={() => setOpen(null)} />
    </Page>
  );
}

export default function Memory() {
  return (
    <Suspense fallback={null}>
      <MemoryPage />
    </Suspense>
  );
}
