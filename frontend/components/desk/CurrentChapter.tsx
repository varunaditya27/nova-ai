"use client";

/**
 * The current chapter — the latest longitudinal theme, or a calm empty line on day one.
 * Never a spinner; the Desk is a quiet place.
 */
export function CurrentChapter({ chapter }: { chapter: string | null }) {
  return (
    <p className="max-w-lg text-lg leading-relaxed text-ink-soft">
      {chapter ?? "No chapter has taken shape yet. That's how every story starts."}
    </p>
  );
}
