"use client";

import { useCallback, useRef, useState } from "react";
import { postChat } from "@/lib/api/client";
import type { TypingSignals } from "@/lib/chat/typingSignals";
import {
  initialStreamState,
  parseSSE,
  streamReducer,
  type StreamState,
} from "@/lib/chat/streamReducer";

// Streaming goes DIRECT to the backend, not through Next's /api rewrite: the dev proxy buffers SSE
// (holds the whole response until close), which would kill token-by-token typing. The backend's
// CORS already allows the frontend origin. JSON endpoints still use the same-origin /api proxy.
const STREAM_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

/**
 * Drives one streamed Nova reply. Reads the SSE body frame-by-frame into a live `text`; on a
 * terminal `error` frame or any transport failure it transparently falls back to the non-streamed
 * POST /chat so the turn still completes. The optimistic user turn is owned by the caller.
 */
export function useChatStream() {
  const [state, setState] = useState<StreamState>(initialStreamState);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => setState(initialStreamState), []);

  const fallback = useCallback(
    async (message: string, sessionId?: string, signals?: TypingSignals): Promise<StreamState> => {
      try {
        const resp = await postChat(message, sessionId, signals);
        const next: StreamState = {
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
        };
        setState(next);
        return next;
      } catch {
        const errored: StreamState = {
          phase: "error",
          text: "",
          echoes: [],
          error: "I lost the thread there — try again?",
        };
        setState(errored);
        return errored;
      }
    },
    []
  );

  const send = useCallback(
    async (message: string, sessionId?: string, signals?: TypingSignals): Promise<StreamState> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      // Mirror the reducer locally so we can RETURN the terminal state (session id, text) without a
      // stale-closure read of React state after the await.
      let local: StreamState = { ...initialStreamState, phase: "streaming" };
      setState(local);

      try {
        const res = await fetch(`${STREAM_BASE}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId, ...signals }),
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
            local = streamReducer(local, frame);
            setState(local);
          }
        }

        if (sawError) return fallback(message, sessionId, signals);
        return local;
      } catch (err) {
        if ((err as Error).name === "AbortError") return local;
        return fallback(message, sessionId, signals);
      }
    },
    [fallback]
  );

  return { state, send, reset };
}
