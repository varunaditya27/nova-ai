/**
 * Layer 1's implicit signals (docs/layer-1-architecture.md §2): how a message was *written*, not
 * just what it says — a long draft cut to two words, a burst of rapid-fire messages, a hesitant
 * start. Captured client-side because the server only ever sees the final text.
 */
export type TypingSignals = {
  user_typing_started_at: string | null;
  deletion_occurred: boolean;
  deletion_count: number;
  peak_draft_length_chars: number;
  final_draft_length_chars: number;
  is_burst: boolean;
  burst_count: number;
  /** Set by the page, not the tracker: this message answers something Nova opened with. */
  is_reply_to_proactive?: boolean;
};

const BURST_WINDOW_MS = 10_000;

export class TypingTracker {
  private startedAt: number | null = null;
  private deletions = 0;
  private peak = 0;
  private prevLength = 0;
  private lastSentAt: number | null = null;
  private burst = 1;

  /** Call on every draft change with the new full text. */
  change(next: string, now: number = Date.now()): void {
    if (this.startedAt === null && next.length > 0) this.startedAt = now;
    if (next.length < this.prevLength) this.deletions += 1;
    this.prevLength = next.length;
    this.peak = Math.max(this.peak, next.length);
  }

  /** Call when sending: returns this message's signals and resets the draft state. */
  snapshot(finalText: string, now: number = Date.now()): TypingSignals {
    const isBurst =
      this.lastSentAt !== null && now - this.lastSentAt <= BURST_WINDOW_MS;
    this.burst = isBurst ? this.burst + 1 : 1;
    const signals: TypingSignals = {
      user_typing_started_at:
        this.startedAt === null ? null : new Date(this.startedAt).toISOString(),
      deletion_occurred: this.deletions > 0,
      deletion_count: this.deletions,
      peak_draft_length_chars: Math.max(this.peak, finalText.length),
      final_draft_length_chars: finalText.length,
      is_burst: this.burst > 1,
      burst_count: this.burst,
    };
    this.lastSentAt = now;
    this.startedAt = null;
    this.deletions = 0;
    this.peak = 0;
    this.prevLength = 0;
    return signals;
  }
}
