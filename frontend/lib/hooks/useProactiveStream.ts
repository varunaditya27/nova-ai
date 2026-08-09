"use client";

import { useEffect, useRef, useState } from "react";
import { markProactiveDelivered } from "@/lib/api/client";
import type { ProactiveStreamItem } from "@/lib/api/types";

// Direct to the backend, not through Next's /api rewrite -- same reasoning as useChatStream: the
// dev proxy buffers SSE (holds the whole response until close), which would defeat a push stream
// entirely. The backend's CORS already allows the frontend origin.
const STREAM_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

/**
 * Live push channel for real, gate-passing Nova-initiated messages (Layer 6 SC-3/SC-4). Opens a
 * native EventSource against GET /proactive/stream; each `item` event is a real, already-
 * validated message (never render `content_basis` -- that's an internal fragment, not something
 * Nova said). The connection is server-bounded (~25 min) and EventSource auto-reconnects on
 * close, so this hook doesn't need its own reconnect logic.
 *
 * Marks each received item "delivered" (POST /proactive/{id}/delivered) as soon as it's surfaced
 * here, closing the SC-5 response-tracking loop for the next chat reply.
 */
export function useProactiveStream() {
  const [items, setItems] = useState<ProactiveStreamItem[]>([]);
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    const source = new EventSource(`${STREAM_BASE}/proactive/stream`);

    source.addEventListener("item", (event) => {
      const item = JSON.parse((event as MessageEvent).data) as ProactiveStreamItem;
      if (seen.current.has(item.item_id)) return;
      seen.current.add(item.item_id);
      setItems((prev) => [item, ...prev]);
      markProactiveDelivered(item.item_id).catch(() => {
        /* best-effort -- a missed delivery ack only means SC-5 can't attribute the next reply */
      });
    });

    // Heartbeats/connected frames need no handling; EventSource's own readyState covers liveness.
    source.onerror = () => {
      /* EventSource retries on its own; nothing to do here for a single-user local app */
    };

    return () => source.close();
  }, []);

  return items;
}
