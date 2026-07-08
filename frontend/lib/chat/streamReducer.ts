/*
 * Pure SSE plumbing for POST /chat/stream. Kept free of React so it's trivially testable.
 * Frame contract (docs/API_REFERENCE.md): one `meta`, then N `token`, then one `done`; a terminal
 * `error` only on failure. Concatenated token text == the delivered, guardrailed reply.
 */
import type { ChatDone, ChatMeta, ChatTokenFrame, Echo } from "@/lib/api/types";

export type StreamFrame =
  | { type: "meta"; data: ChatMeta }
  | { type: "token"; data: ChatTokenFrame }
  | { type: "done"; data: ChatDone }
  | { type: "error"; data: { session_id?: string; message: string } };

export type StreamState = {
  phase: "idle" | "streaming" | "done" | "error";
  text: string;
  meta?: ChatMeta;
  echoes: Echo[];
  sessionId?: string;
  error?: string;
};

export const initialStreamState: StreamState = { phase: "idle", text: "", echoes: [] };

export function streamReducer(state: StreamState, frame: StreamFrame): StreamState {
  switch (frame.type) {
    case "meta":
      return {
        phase: "streaming",
        text: "",
        echoes: [],
        meta: frame.data,
        sessionId: frame.data.session_id,
      };
    case "token":
      return { ...state, phase: "streaming", text: state.text + frame.data.token };
    case "done":
      return {
        ...state,
        phase: "done",
        echoes: frame.data.echoes ?? state.echoes,
        sessionId: frame.data.session_id ?? state.sessionId,
      };
    case "error":
      return {
        ...state,
        phase: "error",
        error: frame.data.message,
        sessionId: frame.data.session_id ?? state.sessionId,
      };
    default:
      return state;
  }
}

function parseFrame(block: string): StreamFrame | null {
  let event = "";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!event || dataLines.length === 0) return null;
  let data: unknown;
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    return null;
  }
  switch (event) {
    case "meta":
      return { type: "meta", data: data as ChatMeta };
    case "token":
      return { type: "token", data: data as ChatTokenFrame };
    case "done":
      return { type: "done", data: data as ChatDone };
    case "error":
      return { type: "error", data: data as { session_id?: string; message: string } };
    default:
      return null;
  }
}

/**
 * Turn a raw text chunk (+ the carried-over buffer) into complete frames. SSE frames end with a
 * blank line (`\n\n`); a chunk can split one, so the trailing incomplete block is returned as the
 * new buffer for the next read.
 */
export function parseSSE(
  chunk: string,
  buffer: string
): { frames: StreamFrame[]; buffer: string } {
  const combined = buffer + chunk;
  const parts = combined.split("\n\n");
  const rest = parts.pop() ?? ""; // last piece may be incomplete
  const frames: StreamFrame[] = [];
  for (const part of parts) {
    if (!part.trim()) continue;
    const frame = parseFrame(part);
    if (frame) frames.push(frame);
  }
  return { frames, buffer: rest };
}
