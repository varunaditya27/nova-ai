"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Empty, Skeleton, Trouble } from "@/components/ui/States";
import { Page } from "@/components/ui/Page";
import { Tabs } from "@/components/ui/Tabs";
import { useAnnotate, useBookmarks, useMilestones } from "@/lib/hooks/useVault";
import { useToast } from "@/lib/hooks/useToast";
import { humanDay } from "@/lib/time";
import type { MessageOut } from "@/lib/api/types";

type Tab = "saved" | "moments";

function Byline({ m }: { m: MessageOut }) {
  return (
    <p className="text-[length:var(--text-small)] text-ink-soft">
      {m.role === "nova" ? "Nova said" : "You said"} · {humanDay(m.created_at)}
    </p>
  );
}

function Links({ m, onRemove }: { m: MessageOut; onRemove: () => void }) {
  return (
    <p className="mt-2 flex flex-wrap gap-x-5 text-[length:var(--text-small)]">
      <Link
        href={`/?m=${m.message_id}`}
        className="inline-flex min-h-9 items-center text-accent underline underline-offset-4"
      >
        See it in the conversation
      </Link>
      <button
        onClick={onRemove}
        className="inline-flex min-h-9 items-center text-ink-soft underline underline-offset-4 hover:text-ink"
      >
        Remove
      </button>
    </p>
  );
}

function Saved() {
  const q = useBookmarks();
  const { bookmark } = useAnnotate();
  const { toast } = useToast();
  const folders = useMemo(() => {
    const groups = new Map<string, MessageOut[]>();
    for (const m of q.data ?? []) {
      const key = m.bookmark_category || "Saved without a folder";
      groups.set(key, [...(groups.get(key) ?? []), m]);
    }
    return [...groups.entries()];
  }, [q.data]);

  if (q.isLoading) return <Skeleton lines={4} />;
  if (q.isError)
    return (
      <Trouble
        what="Your saved messages couldn’t be loaded just now."
        onRetry={() => q.refetch()}
      />
    );
  if (folders.length === 0) {
    return (
      <Empty title="Nothing saved yet.">
        When Nova says something worth keeping — advice, a line that made you
        laugh, a hard-won idea — hover over it in the conversation and choose
        “Save”. You can file it under a name of your own.
      </Empty>
    );
  }
  return (
    <div className="flex flex-col gap-14">
      {folders.map(([name, items]) => (
        <section key={name} aria-label={name}>
          <h2 className="mb-5 text-[length:var(--text-read)]">{name}</h2>
          <ul className="flex max-w-3xl flex-col gap-8">
            {items.map((m) => (
              <li key={m.message_id}>
                <blockquote className="read whitespace-pre-wrap">
                  {m.content}
                </blockquote>
                <Byline m={m} />
                <Links
                  m={m}
                  onRemove={() =>
                    bookmark.mutate(
                      { id: m.message_id, on: false },
                      { onSuccess: () => toast("Removed from Keepsakes") },
                    )
                  }
                />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function Moments() {
  const q = useMilestones();
  const { milestone } = useAnnotate();
  const { toast } = useToast();
  if (q.isLoading) return <Skeleton lines={4} />;
  if (q.isError)
    return (
      <Trouble
        what="Your moments couldn’t be loaded just now."
        onRetry={() => q.refetch()}
      />
    );
  const items = q.data ?? [];
  if (items.length === 0) {
    return (
      <Empty title="No moments marked yet.">
        Some things you say change your life — getting in, quitting, finishing
        something hard. Hover over the message in the conversation and choose
        “This mattered”, and it will be kept here like a photograph.
      </Empty>
    );
  }
  return (
    <ul className="flex max-w-4xl flex-col gap-14">
      {items.map((m) => (
        <li key={m.message_id}>
          <p className="mb-3 inline-flex items-center gap-2 text-[length:var(--text-read)]">
            <span aria-hidden className="size-3 rounded-full bg-earned" />
            {m.milestone_label || "A moment that mattered"}
          </p>
          <blockquote className="font-display text-[length:var(--text-title)] leading-[1.15]">
            “{m.content}”
          </blockquote>
          <div className="mt-3">
            <Byline m={m} />
          </div>
          <Links
            m={m}
            onRemove={() =>
              milestone.mutate(
                { id: m.message_id, on: false },
                { onSuccess: () => toast("No longer marked as a moment") },
              )
            }
          />
        </li>
      ))}
    </ul>
  );
}

/** Keepsakes: what you chose to hold on to. Messages you saved, and moments that mattered. */
export default function Keepsakes() {
  const [tab, setTab] = useState<Tab>("moments");
  return (
    <Page
      title="Keepsakes"
      intro="Messages you saved, and moments you marked as mattering, from your conversations."
      actions={
        <Tabs
          label="Kind of keepsake"
          value={tab}
          onChange={setTab}
          items={[
            { value: "moments", label: "Moments that mattered" },
            { value: "saved", label: "Saved messages" },
          ]}
        />
      }
    >
      {tab === "moments" ? <Moments /> : <Saved />}
    </Page>
  );
}
