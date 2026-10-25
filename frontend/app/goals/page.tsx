"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Page } from "@/components/ui/Page";
import { Tabs } from "@/components/ui/Tabs";
import { Meter } from "@/components/ui/Bits";
import { Empty, Skeleton, Trouble } from "@/components/ui/States";
import { useCreateGoal, useGoals } from "@/lib/hooks/useNovaState";
import { useToast } from "@/lib/hooks/useToast";
import {
  habitCadence,
  isFinished,
  statusWords,
  streakWords,
} from "@/lib/goals";
import { countdown } from "@/lib/time";
import type { Goal } from "@/lib/api/types";

type Tab = "active" | "completed" | "abandoned";

function Row({ g }: { g: Goal }) {
  const next = g.milestones.find((m) => m.status !== "reached");
  const habit = g.habits[0];
  return (
    <li className="rule-top">
      <Link
        href={`/goals/${g.goal_id}`}
        className="group block px-4 py-5 transition-colors hover:bg-surface"
      >
        <div className="flex items-start justify-between gap-4">
          <p className="font-display text-[length:var(--text-title)] leading-tight">
            {g.title}
          </p>
          <ArrowRight
            aria-hidden
            className="mt-2 shrink-0 text-ink-soft transition-transform group-hover:translate-x-1"
          />
        </div>
        <p className="mt-1 text-ink-soft">
          {statusWords(g.status)}
          {g.deadline
            ? ` · ${countdown(g.deadline)}${g.deadline_description ? ` (${g.deadline_description})` : ""}`
            : ""}
        </p>
        <Meter
          value={g.progress_score}
          earned={isFinished(g.status)}
          label={`Progress on ${g.title}`}
          className="mt-4 max-w-xl"
        />
        {(next || habit) && (
          <p className="mt-3 text-[length:var(--text-small)] text-ink-soft">
            {next
              ? `Next step: ${next.title}${next.target_date ? ` · ${countdown(next.target_date)}` : ""}`
              : ""}
            {next && habit ? " — " : ""}
            {habit
              ? `${habit.title} ${habitCadence(habit.frequency)}: ${streakWords(habit.current_streak, habit.frequency)}`
              : ""}
          </p>
        )}
      </Link>
    </li>
  );
}

/** Goals: what you're working toward. Nova notices them in conversation; you can also add one yourself. */
export default function Goals() {
  const [tab, setTab] = useState<Tab>("active");
  const q = useGoals(tab === "active" ? undefined : tab);
  const create = useCreateGoal();
  const { toast } = useToast();
  const [title, setTitle] = useState("");

  const add = () => {
    const t = title.trim();
    if (!t) return;
    create.mutate(
      { title: t },
      {
        onSuccess: () =>
          toast("Goal added", "Nova will keep track of it with you."),
        onError: () => toast("Couldn’t add that just now", "Please try again."),
      },
    );
    setTitle("");
  };

  return (
    <Page
      title="Goals"
      intro="Mention a goal in conversation — “I want to finish my course by December” — and Nova adds it, breaks it into steps, and checks in. You can also add one here."
      actions={
        <Tabs
          label="Which goals"
          value={tab}
          onChange={setTab}
          items={[
            { value: "active", label: "In progress" },
            { value: "completed", label: "Done" },
            { value: "abandoned", label: "Set aside" },
          ]}
        />
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          add();
        }}
        className="tone mb-10 flex max-w-2xl items-center gap-3 fold-sm px-5 py-2"
      >
        <label htmlFor="new-goal" className="sr-only">
          A goal to add
        </label>
        <input
          id="new-goal"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Add a goal yourself…"
          className="min-h-11 flex-1 bg-transparent outline-none placeholder:text-mute"
        />
        <button
          type="submit"
          disabled={!title.trim() || create.isPending}
          className="min-h-11 fold-sm bg-accent px-6 text-accent-ink disabled:opacity-50"
        >
          Add goal
        </button>
      </form>

      {q.isLoading ? (
        <Skeleton lines={4} />
      ) : q.isError ? (
        <Trouble
          what="Your goals couldn’t be loaded just now."
          onRetry={() => q.refetch()}
        />
      ) : (q.data ?? []).length === 0 ? (
        <Empty
          title={
            tab === "active"
              ? "No goals in progress."
              : tab === "completed"
                ? "Nothing finished yet."
                : "Nothing set aside."
          }
        >
          {tab === "active"
            ? "When you tell Nova about something you want to do, it appears here with its steps and any habits that will help."
            : tab === "completed"
              ? "Goals you finish are kept here, so you can look back at what you’ve done."
              : "Goals you let go of rest here. There’s no shame in changing your mind."}
        </Empty>
      ) : (
        <ul className="flex max-w-3xl flex-col">
          {q.data?.map((g) => (
            <Row key={g.goal_id} g={g} />
          ))}
        </ul>
      )}
    </Page>
  );
}
