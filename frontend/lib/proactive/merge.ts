import type { ProactiveItem, ProactiveStreamItem } from "@/lib/api/types";

export type ShownProactiveItem = {
  item_id: string;
  item_type: string;
  message: string;
  current_priority: number;
};

/**
 * Merge the polled baseline (GET /proactive, only items with a real message) with live-pushed
 * SSE items, deduplicated by item_id and sorted highest-priority first. Stream items win on
 * overlap since they're already known-delivered (POST /proactive/{id}/delivered already fired).
 */
export function mergeProactiveItems(
  polled: ProactiveItem[],
  streamed: ProactiveStreamItem[]
): ShownProactiveItem[] {
  const byId = new Map<string, ShownProactiveItem>();
  for (const p of polled) {
    if (p.message) byId.set(p.item_id, p);
  }
  for (const s of streamed) {
    byId.set(s.item_id, s);
  }
  return Array.from(byId.values()).sort((a, b) => b.current_priority - a.current_priority);
}
