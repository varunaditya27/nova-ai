/*
 * API response types, transcribed from docs/API_REFERENCE.md. Extended in later tasks;
 * Echo is defined here because the conversation primitives (Task 5) consume it first.
 */

/** A memory Nova recalled while writing a reply — the one permitted ambient element. */
export type Echo = {
  summary: string;
  when: string;
  created_at: string | null;
};
