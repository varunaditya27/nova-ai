import type { MessageOut } from "@/lib/api/types";
import { humanDay } from "@/lib/time";

export type Sitting = {
  /** Stable key: the first message's id. */
  key: string;
  /** "Yesterday evening", "Tuesday night", "12 October" — when this conversation began. */
  heading: string;
  /** Set when a long silence came before this sitting: "A week passes." */
  passage: string | null;
  messages: MessageOut[];
};

const DAY = 86_400_000;

/** A silence worth marking, in words. Nothing under three days — ordinary gaps aren't events. */
export function passageOfTime(ms: number): string | null {
  const days = Math.floor(ms / DAY);
  if (days < 3) return null;
  if (days < 7) return `${days} days pass.`;
  if (days < 14) return "A week passes.";
  if (days < 60) return `${Math.floor(days / 7)} weeks pass.`;
  if (days < 365) return `${Math.floor(days / 30)} months pass.`;
  const years = Math.floor(days / 365);
  return years === 1 ? "A year passes." : `${years} years pass.`;
}

/**
 * Split the (oldest → newest) thread into sittings: a new one starts when the server-owned session
 * changes. The thread stays one continuous conversation; sittings are only how it is *read*.
 */
export function groupSittings(
  messages: MessageOut[],
  now: Date = new Date(),
): Sitting[] {
  const sittings: Sitting[] = [];
  let prev: MessageOut | undefined;
  for (const m of messages) {
    const current = sittings[sittings.length - 1];
    if (!current || (prev && m.session_key !== prev.session_key)) {
      const gap =
        prev?.created_at && m.created_at
          ? new Date(m.created_at).getTime() -
            new Date(prev.created_at).getTime()
          : 0;
      sittings.push({
        key: m.message_id,
        heading: humanDay(m.created_at, now),
        passage: prev ? passageOfTime(gap) : null,
        messages: [m],
      });
    } else {
      current.messages.push(m);
    }
    prev = m;
  }
  return sittings;
}
