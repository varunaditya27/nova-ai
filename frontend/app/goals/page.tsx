"use client";

import { useState } from "react";
import { PageShell } from "@/components/primitives/PageShell";
import { CarvedButton } from "@/components/primitives/CarvedButton";
import { GoalCard } from "@/components/goals/GoalCard";
import { useCreateGoal, useGoals } from "@/lib/hooks/useNovaState";

/** Goals — some the user named, some Nova extracted from chat. Brass marks a finished one. */
export default function Goals() {
  const { data, isLoading } = useGoals();
  const create = useCreateGoal();
  const [title, setTitle] = useState("");

  const add = () => {
    const t = title.trim();
    if (!t) return;
    create.mutate({ title: t });
    setTitle("");
  };

  return (
    <PageShell
      title="What you're working toward"
      description="Some you named, some Nova noticed. It keeps gentle track."
    >
      <div className="mb-8 flex gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="Name a goal…"
          className="flex-1 rounded-md border border-hairline bg-surface px-3 py-2 text-sm text-ink outline-none placeholder:text-ink-faint"
        />
        <CarvedButton onClick={add} disabled={!title.trim() || create.isPending}>
          Add
        </CarvedButton>
      </div>

      {isLoading && <div className="h-20 rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">Nothing yet. Name something you want — or just mention it in chat.</p>
      )}

      <div className="flex flex-col gap-3">
        {data?.map((g) => (
          <GoalCard key={g.goal_id} goal={g} />
        ))}
      </div>
    </PageShell>
  );
}
