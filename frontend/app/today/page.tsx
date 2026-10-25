"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { Avatar, Meter } from "@/components/ui/Bits";
import { ButtonLink } from "@/components/ui/Button";
import { Skeleton, Trouble } from "@/components/ui/States";
import { useHome } from "@/lib/hooks/useHome";
import {
  useGoals,
  useProactive,
  useRelationship,
} from "@/lib/hooks/useNovaState";
import { usePeople } from "@/lib/hooks/usePeople";
import { usePendingTools } from "@/lib/hooks/useTools";
import { rise, stagger } from "@/lib/motion";
import { relationshipLabel } from "@/lib/people";
import { stageById, toNextStage } from "@/lib/stages";
import { countdown, humanDay, relativeTime } from "@/lib/time";
import { hello } from "@/lib/voice";
import { Mark } from "@/components/ui/Mark";
import { Margin } from "@/components/brand/Margin";
import { upcoming } from "@/lib/upcoming";

function whenWeLastTalked(iso: string | null): string {
  if (!iso) return "";
  const ago = Date.now() - new Date(iso).getTime();
  if (ago < 2 * 3_600_000) return "We were just talking.";
  return `We last talked ${relativeTime(iso)}.`;
}

/** Today: walking into the room. What Nova has on its mind, where you left off, what's coming. */
export default function Today() {
  const home = useHome();
  const goals = useGoals();
  const people = usePeople();
  const rel = useRelationship();
  const polled = useProactive().data;
  const errands = usePendingTools().data ?? [];

  if (home.isLoading) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-16 sm:px-8 lg:px-12">
        <Skeleton lines={2} className="max-w-xl" />
      </div>
    );
  }
  if (home.isError || !home.data) {
    return (
      <div className="mx-auto max-w-3xl px-5 pt-16 sm:px-8">
        <Trouble
          what="Today couldn’t be put together just now."
          onRetry={() => home.refetch()}
        />
      </div>
    );
  }

  const h = home.data;
  const onMind =
    h.top_proactive ?? polled?.find((i) => i.message)?.message ?? null;
  const active = (goals.data ?? []).filter(
    (g) => g.status !== "completed" && g.status !== "abandoned",
  );
  const soon = upcoming(goals.data ?? []).slice(0, 5);
  const topPeople = [...(people.data ?? [])]
    .sort((a, b) => b.mention_count - a.mention_count)
    .slice(0, 6);
  const stage = stageById(h.relationship_stage);
  const next = rel.data
    ? toNextStage(h.relationship_stage, rel.data.total_sessions)
    : null;
  const first = h.message_count === 0;
  const { headline, aside } = hello(new Date(), h.name);

  return (
    <motion.div
      variants={stagger(0.08)}
      initial="hidden"
      animate="show"
      className="mx-auto flex max-w-6xl flex-col gap-16 px-5 pb-28 pt-10 sm:px-8 lg:gap-20 lg:px-12 lg:pt-16"
    >
      <motion.header variants={rise} className="flex flex-col gap-4">
        <div className="flex items-end gap-4">
          <Mark size={56} alive />
          <Margin tilt={-3} className="pb-2">
            {aside}
          </Margin>
        </div>
        <h1 className="text-[length:var(--text-display)]">{headline}</h1>
        <p className="read max-w-2xl text-ink-soft">
          {first
            ? "This is where our life together will gather. For now it’s a blank page, and I’m rather fond of it."
            : whenWeLastTalked(h.last_interaction_at)}
        </p>
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <ButtonLink href="/">
            {first ? "Say the first thing" : "Pick up the conversation"}{" "}
            <ArrowRight size={18} aria-hidden />
          </ButtonLink>
          {errands.length > 0 && (
            <ButtonLink href="/errands" variant="quiet">
              {errands.length === 1 ? "1 thing" : `${errands.length} things`}{" "}
              waiting for your OK
            </ButtonLink>
          )}
        </div>
      </motion.header>

      {h.cold_start_active && (
        <motion.section variants={rise} className="tone max-w-3xl px-7 py-6">
          <h2 className="rule-top pt-4 text-[length:var(--text-read)]">
            I’m still getting to know you
          </h2>
          <p className="mt-2 text-ink-soft">
            For the first few conversations I stay gentle: I ask little, bring up nothing from the past, and won’t reach out first. That changes as I learn your rhythm.
          </p>
        </motion.section>
      )}

      <motion.div
        variants={rise}
        className="grid gap-10 lg:grid-cols-12 lg:gap-14"
      >
        <section aria-labelledby="mind" className="lg:col-span-7">
          <h2
            id="mind"
            className="rule-top pt-4 mb-4 text-[length:var(--text-read)] text-ink-soft"
          >
            On my mind
          </h2>
          {onMind ? (
            <>
              <p className="font-display text-[length:var(--text-title)] leading-[1.15]">
                “{onMind}”
              </p>
              <div className="mt-5">
                <ButtonLink href="/" variant="quiet">
                  Talk about it
                </ButtonLink>
              </div>
            </>
          ) : (
            <p className="read max-w-lg text-ink-soft">
              Nothing pressing. When I have something worth saying, I’ll bring
              it up. I don’t talk just to fill the quiet.
            </p>
          )}
        </section>

        <section
          aria-labelledby="left-off"
          className="tone self-start px-7 py-7 lg:col-span-5"
        >
          <h2
            id="left-off"
            className="rule-top pt-4 mb-3 text-[length:var(--text-read)] text-ink-soft"
          >
            Where we are in your story
          </h2>
          {h.current_chapter ? (
            <p className="read">{h.current_chapter}</p>
          ) : (
            <p className="text-ink-soft">
              I write a chapter for each week. The first one turns up after
              we’ve been talking for a few days. No spoilers.
            </p>
          )}
          <Link
            href="/story"
            className="mt-4 inline-flex min-h-11 items-center gap-1 text-accent underline underline-offset-4"
          >
            Read our story <ArrowRight size={16} aria-hidden />
          </Link>
        </section>
      </motion.div>

      <motion.div
        variants={rise}
        className="grid gap-12 lg:grid-cols-2 lg:gap-16"
      >
        <section aria-labelledby="coming">
          <h2
            id="coming"
            className="rule-top pt-4 mb-4 text-[length:var(--text-read)] text-ink-soft"
          >
            Coming up
          </h2>
          {goals.isLoading ? (
            <Skeleton lines={3} />
          ) : soon.length === 0 ? (
            <p className="text-ink-soft">
              Nothing due in the next month. Tell me about a deadline or a plan
              and it will turn up here, with a countdown I’ll try not to
              overplay.
            </p>
          ) : (
            <ul className="flex flex-col gap-5">
              {soon.map((u) => (
                <li key={u.key}>
                  <p className="read">{u.what}</p>
                  <p className="text-[length:var(--text-small)] text-ink-soft">
                    <Link
                      href={`/goals/${u.goalId}`}
                      className="underline underline-offset-4"
                    >
                      {u.goalTitle}
                    </Link>{" "}
                    · {countdown(u.date)} · {humanDay(u.date)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="motion">
          <h2
            id="motion"
            className="rule-top pt-4 mb-4 text-[length:var(--text-read)] text-ink-soft"
          >
            Goals in motion
          </h2>
          {goals.isLoading ? (
            <Skeleton lines={3} />
          ) : active.length === 0 ? (
            <p className="text-ink-soft">
              No goals yet. Mention something you’re working toward and I’ll
              keep track of it, and nudge you at sensible intervals.
            </p>
          ) : (
            <ul className="flex flex-col gap-5">
              {active.slice(0, 4).map((g) => (
                <li key={g.goal_id}>
                  <Link href={`/goals/${g.goal_id}`} className="read block">
                    {g.title}
                  </Link>
                  <Meter
                    value={g.progress_score}
                    label={`Progress on ${g.title}`}
                    className="mt-2"
                  />
                </li>
              ))}
            </ul>
          )}
        </section>
      </motion.div>

      {topPeople.length > 0 && (
        <motion.section variants={rise} aria-labelledby="people">
          <h2
            id="people"
            className="rule-top pt-4 mb-5 text-[length:var(--text-read)] text-ink-soft"
          >
            The people you talk about most
          </h2>
          <ul className="flex flex-wrap gap-x-8 gap-y-5">
            {topPeople.map((p) => (
              <li key={p.person_id}>
                <Link
                  href={`/people/${p.person_id}`}
                  className="flex items-center gap-3"
                >
                  <Avatar name={p.display_name} size={52} />
                  <span>
                    <span className="block">{p.display_name}</span>
                    <span className="block text-[length:var(--text-small)] text-ink-soft">
                      {relationshipLabel(p.relationship_type)}
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </motion.section>
      )}

      <motion.section
        variants={rise}
        aria-labelledby="us"
        className="max-w-3xl"
      >
        <h2
          id="us"
          className="rule-top pt-4 mb-3 text-[length:var(--text-read)] text-ink-soft"
        >
          How we’re doing
        </h2>
        <p className="font-display text-[length:var(--text-title)] leading-[1.15]">
          {stage.name}.
        </p>
        <p className="read mt-3 text-ink-soft">
          {stage.meaning}
          {next
            ? ` About ${next.remaining} more ${next.remaining === 1 ? "conversation" : "conversations"} until “${next.next.name.toLowerCase()}”.`
            : ""}
        </p>
        <Link
          href="/us"
          className="mt-3 inline-flex min-h-11 items-center gap-1 text-accent underline underline-offset-4"
        >
          How I know you <ArrowRight size={16} aria-hidden />
        </Link>
      </motion.section>
    </motion.div>
  );
}
