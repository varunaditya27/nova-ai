"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { getMessages } from "@/lib/api/client";
import type { MessageOut } from "@/lib/api/types";

const PAGE = 40;

/**
 * Flatten the newest-first pages React Query accumulates into one ascending, deduped thread
 * (oldest → newest) so the UI can render it top-to-bottom and continue from the bottom.
 * Pure and exported so it can be unit-tested without a live query.
 */
export function mergePages(pages: MessageOut[][]): MessageOut[] {
  const byCursor = new Map<number, MessageOut>();
  for (const page of pages) {
    for (const m of page) byCursor.set(m.cursor, m);
  }
  return [...byCursor.values()].sort((a, b) => a.cursor - b.cursor);
}

/** The single permanent thread, paged backwards by cursor. `messages` is oldest → newest. */
export function useMessages() {
  const query = useInfiniteQuery({
    queryKey: ["messages"],
    queryFn: ({ pageParam }) => getMessages({ limit: PAGE, before: pageParam }),
    initialPageParam: undefined as number | undefined,
    // "Next page" here means OLDER: the last (oldest) item of the newest-first page is the cursor
    // to fetch before. A short page means we've reached the start of the relationship.
    getNextPageParam: (lastPage) =>
      lastPage.length < PAGE ? undefined : lastPage[lastPage.length - 1].cursor,
  });

  return {
    ...query,
    messages: query.data ? mergePages(query.data.pages) : [],
  };
}
