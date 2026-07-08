"use client";

import { useCallback, useRef, useState } from "react";
import { postChat } from "@/lib/api/client";
import {
  initialStreamState,
  parseSSE,
  streamReducer,
  type StreamState,
} from "@/lib/chat/streamReducer";

/**
 * Drives one streamed Nova reply. Reads the SSE body frame-by-frame into a live `text`; on a
 * terminal `error` frame or any transport failure it transparently falls back to the non-streamed
 * POST /chat so the turn still completes. The optimistic user turn is owned by the caller.
 */
export function useChatStream() {
  const [state, setState] = useState<StreamState>(initialStreamState);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => setState(initialStreamState), []);

  const fallback = useCallback(async (message: string, sessionId?: string) => {
    try {
      const resp = await postChat(message, sessionId);
      setState({
        phase: "done",
        text: resp.response,
        echoes: resp.echoes ?? [],
        sessionId: resp.session_id,
        meta: {
          session_id: resp.session_id,
          conversation_mode: resp.conversation_mode,
          cognitive_system: resp.cognitive_system,
          crisis_active: resp.crisis_active,
          refined: resp.refined,
          confabulation_guard: resp.confabulation_guard,
        },
      });
    } catch {
      setState((prev) => ({
        ...prev,
        phase: "error",
        error: "I lost the thread there — try again?",
      }));
    }
  }, []);

  const send = useCallback(
    async (message: string, sessionId?: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setState({ ...initialStreamState, phase: "streaming" });

      try {
        const res = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error(`stream ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let sawError = false;

        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          const { frames, buffer: next } = parseSSE(
            decoder.decode(value, { stream: true }),
            buffer
          );
          buffer = next;
          for (const frame of frames) {
            if (frame.type === "error") sawError = true;
            setState((prev) => streamReducer(prev, frame));
          }
        }

        if (sawError) await fallback(message, sessionId);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        await fallback(message, sessionId);
      }
    },
    [fallback]
  );

  return { state, send, reset };
}
