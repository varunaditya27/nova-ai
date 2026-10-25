"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Page } from "@/components/ui/Page";
import { Button } from "@/components/ui/Button";
import { Meter } from "@/components/ui/Bits";
import { Skeleton, Trouble } from "@/components/ui/States";
import {
  useDeleteGoal,
  useGoal,
  useUpdateGoal,
} from "@/lib/hooks/useNovaState";
import { useToast } from "@/lib/hooks/useToast";
import {
  habitCadence,
  isFinished,
  statusWords,
  streakWords,
} from "@/lib/goals";
import { countdown, longDate } from "@/lib/time";
import { cn } from "@/lib/cn";

/** One goal in full: how far along, the steps on the way, the habits that help, and your say over it. */
export default function GoalDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const q = useGoal(id);
  const update = useUpdateGoal();
  const del = useDeleteGoal();
  const { toast } = useToast();
  const [confirming, setConfirming] = useState(false);
  const [draft, setDraft] = useState<number | null>(null);

  if (q.isLoading)
    return (
      <Page title="…">
        <Skeleton lines={4} />
      </Page>
    );
  if (q.isError || !q.data) {
    return (
      <Page title="Goal">
        <Trouble
          what="This goal couldn’t be found. It may have been removed."
          onRetry={() => q.refetch()}
        />
      </Page>
    );
  }
  const g = q.data;
  const done = isFinished(g.status);
  const shown = draft ?? g.progress_score;
  const patch = (
    p: { status?: string; progress_score?: number },
    message: string,
  ) =>
    update.mutate(
      { id: g.goal_id, patch: p },
      { onSuccess: () => toast(message) },
    );

  return (
    <Page
      title={g.title}
      intro={`${statusWords(g.status)}${
        g.deadline
          ? ` · ${countdown(g.deadline)}, ${longDate(g.deadline)}`
          : g.deadline_description
            ? ` · ${g.deadline_description}`
            : ""
      }`}
      actions={
        <Link
          href="/goals"
          className="inline-flex min-h-11 items-center gap-2 cut-sm bg-sunk px-5 hover:bg-raised"
        >
          <ArrowLeft size={16} aria-hidden /> All goals
        </Link>
      }
    >
      {g.description && <p className="read mb-10 max-w-2xl">{g.description}</p>}

      <section aria-labelledby="progress" className="mb-14 max-w-2xl">
        <h2 id="progress" className="mb-4 text-[length:var(--text-read)]">
          How far along
        </h2>
        <Meter value={shown} earned={done} label={`Progress on ${g.title}`} />
        <label htmlFor="slider" className="mt-4 block text-ink-soft">
          You can set this yourself: {Math.round(shown * 100)}% of the way
        </label>
        <input
          id="slider"
          type="range"
          min={0}
          max={100}
          step={5}
          value={Math.round(shown * 100)}
          onChange={(e) => setDraft(Number(e.target.value) / 100)}
          onPointerUp={() =>
            draft !== null &&
            patch({ progress_score: draft }, "Progress updated")
          }
          onKeyUp={() =>
            draft !== null &&
            patch({ progress_score: draft }, "Progress updated")
          }
          className="mt-2 w-full accent-[var(--accent)]"
        />
        <p className="mt-2 text-[length:var(--text-small)] text-mute">
          Nova also updates this on its own from what you tell it.
        </p>
      </section>

      <div className="grid gap-14 lg:grid-cols-2">
        <section aria-labelledby="steps">
          <h2 id="steps" className="mb-5 text-[length:var(--text-read)]">
            The steps on the way
          </h2>
          {g.milestones.length === 0 ? (
            <p className="max-w-md text-ink-soft">
              No steps yet. Nova breaks a goal into steps once it has enough
              detail about what you’re aiming for.
            </p>
          ) : (
            <ol className="relative flex flex-col gap-6 pl-9">
              <span
                aria-hidden
                className="absolute bottom-2 left-[7px] top-2 w-[3px] cut-sm bg-sunk"
              />
              {g.milestones.map((m) => {
                const reached = m.status === "reached";
                return (
                  <li key={m.title} className="relative">
                    <span
                      aria-hidden
                      className={cn(
                        "absolute -left-9 top-1.5 size-[17px] cut-sm",
                        reached ? "bg-earned" : "bg-ink-soft",
                      )}
                    />
                    <p className="read">{m.title}</p>
                    <p className="text-[length:var(--text-small)] text-ink-soft">
                      {reached ? "Done" : "Still ahead"}
                      {m.target_date
                        ? ` · ${reached ? "" : `${countdown(m.target_date)}, `}${longDate(m.target_date)}`
                        : ""}
                    </p>
                  </li>
                );
              })}
            </ol>
          )}
        </section>

        <section aria-labelledby="habits">
          <h2 id="habits" className="mb-5 text-[length:var(--text-read)]">
            Habits that help
          </h2>
          {g.habits.length === 0 ? (
            <p className="max-w-md text-ink-soft">
              No habits yet. When Nova suggests a routine and you adopt it, it’s
              tracked here.
            </p>
          ) : (
            <ul className="flex flex-col gap-7">
              {g.habits.map((h) => (
                <li key={h.title}>
                  <p className="read">
                    {h.title}{" "}
                    <span className="text-ink-soft">
                      · {habitCadence(h.frequency)}
                    </span>
                  </p>
                  <p className="mt-1">
                    {streakWords(h.current_streak, h.frequency)}
                  </p>
                  <div aria-hidden className="mt-2 flex flex-wrap gap-1.5">
                    {Array.from({
                      length: Math.min(
                        Math.max(h.best_streak, h.current_streak, 7),
                        21,
                      ),
                    }).map((_, i) => (
                      <span
                        key={i}
                        className={cn(
                          "size-3.5 rounded-full",
                          i < h.current_streak ? "bg-accent" : "bg-sunk",
                        )}
                      />
                    ))}
                  </div>
                  <p className="mt-2 text-[length:var(--text-small)] text-ink-soft">
                    Best run: {h.best_streak} · checked in {h.total_check_ins}{" "}
                    {h.total_check_ins === 1 ? "time" : "times"} in all
                  </p>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-6 max-w-md text-[length:var(--text-small)] text-mute">
            You don’t need to tick anything off — tell Nova when you’ve done it
            (“I went for a run this morning”) and it counts.
          </p>
        </section>
      </div>

      <section
        aria-label="Change this goal"
        className="mt-16 flex flex-wrap items-center gap-3"
      >
        {done ? (
          <Button
            variant="quiet"
            onClick={() => patch({ status: "active" }, "Goal reopened")}
          >
            Reopen this goal
          </Button>
        ) : (
          <Button
            onClick={() =>
              patch(
                { status: "completed", progress_score: 1 },
                "Marked as done — well done",
              )
            }
          >
            I’ve done it
          </Button>
        )}
        {g.status !== "abandoned" && !done && (
          <Button
            variant="quiet"
            onClick={() => patch({ status: "abandoned" }, "Set aside")}
          >
            Set it aside
          </Button>
        )}
        {g.status === "abandoned" && (
          <Button
            variant="quiet"
            onClick={() => patch({ status: "active" }, "Back in progress")}
          >
            Pick it back up
          </Button>
        )}
        {!confirming ? (
          <Button variant="text" onClick={() => setConfirming(true)}>
            Delete this goal
          </Button>
        ) : (
          <span className="tone-sunk flex flex-wrap items-center gap-3 px-5 py-3">
            Delete it for good?
            <Button
              variant="danger"
              onClick={() =>
                del.mutate(g.goal_id, {
                  onSuccess: () => {
                    toast("Goal deleted");
                    router.push("/goals");
                  },
                })
              }
            >
              Yes, delete
            </Button>
            <Button variant="quiet" onClick={() => setConfirming(false)}>
              Keep it
            </Button>
          </span>
        )}
      </section>
    </Page>
  );
}
