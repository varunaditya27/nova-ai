"use client";

import { useState } from "react";
import { Check, Minus, Plus, RotateCcw } from "lucide-react";
import { Surface } from "@/components/primitives/Surface";
import { Meter } from "@/components/primitives/Meter";
import { useDeleteGoal, useUpdateGoal } from "@/lib/hooks/useNovaState";
import type { Goal } from "@/lib/api/types";

/** A goal with live controls: adjust progress, mark done (earned brass), reopen, or remove. */
export function GoalCard({ goal }: { goal: Goal }) {
  const update = useUpdateGoal();
  const del = useDeleteGoal();
  const [confirming, setConfirming] = useState(false);
  const done = goal.status === "completed" || goal.progress_score >= 1;

  const nudge = (delta: number) => {
    const next = Math.max(0, Math.min(1, Math.round((goal.progress_score + delta) * 100) / 100));
    update.mutate({ id: goal.goal_id, patch: { progress_score: next } });
  };

  return (
    <Surface className="p-5">
      <div className="flex items-baseline justify-between gap-3">
        <p className="font-display text-lg text-ink">{goal.title}</p>
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          {goal.status.replace(/_/g, " ")}
        </span>
      </div>
      {goal.description && <p className="mt-1 text-sm text-ink-soft">{goal.description}</p>}
      <Meter value={goal.progress_score} brass={done} className="mt-3" />

      <div className="mt-3 flex items-center gap-1 text-ink-faint">
        <button onClick={() => nudge(-0.1)} aria-label="Less progress" className="rounded-sm p-1 hover:text-ink-soft">
          <Minus size={13} />
        </button>
        <span className="w-9 text-center font-mono text-[11px] text-ink-soft">
          {Math.round(goal.progress_score * 100)}%
        </span>
        <button onClick={() => nudge(0.1)} aria-label="More progress" className="rounded-sm p-1 hover:text-ink-soft">
          <Plus size={13} />
        </button>

        <span className="mx-2 h-4 w-px bg-hairline" aria-hidden />

        {done ? (
          <button
            onClick={() => update.mutate({ id: goal.goal_id, patch: { status: "active" } })}
            className="inline-flex items-center gap-1 rounded-sm px-1.5 py-1 text-[11px] hover:text-ink-soft"
          >
            <RotateCcw size={12} /> reopen
          </button>
        ) : (
          <button
            onClick={() =>
              update.mutate({ id: goal.goal_id, patch: { status: "completed", progress_score: 1 } })
            }
            className="inline-flex items-center gap-1 rounded-sm px-1.5 py-1 text-[11px] hover:text-brass"
          >
            <Check size={12} /> mark done
          </button>
        )}

        <span className="flex-1" />

        {confirming ? (
          <span className="inline-flex items-center gap-2 text-[11px]">
            <button onClick={() => del.mutate(goal.goal_id)} className="text-brass hover:underline">
              remove?
            </button>
            <button onClick={() => setConfirming(false)} className="hover:text-ink">
              keep
            </button>
          </span>
        ) : (
          <button
            onClick={() => setConfirming(true)}
            className="rounded-sm px-1.5 py-1 text-[11px] hover:text-ink-soft"
          >
            remove
          </button>
        )}
      </div>
    </Surface>
  );
}
