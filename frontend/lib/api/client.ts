/*
 * The typed API client. Every call is same-origin against /api/* (Next rewrites to FastAPI).
 * JSON/blob endpoints live here; the SSE stream is read directly in useChatStream (Task 8).
 */
import {
  ApiError,
  type CalendarOut,
  type ChatResponse,
  type HomeOut,
  type LongitudinalSummary,
  type MemoryOut,
  type MessageOut,
  type MuseumOut,
} from "./types";

const BASE = "/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const jsonPost = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function getHome(): Promise<HomeOut> {
  return requestJson<HomeOut>("/home");
}

export function getMessages(
  params: { limit?: number; before?: number } = {}
): Promise<MessageOut[]> {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.before != null) q.set("before", String(params.before));
  const qs = q.toString();
  return requestJson<MessageOut[]>(`/messages${qs ? `?${qs}` : ""}`);
}

export function searchMessages(
  query: string,
  opts: { start?: string; end?: string; limit?: number } = {}
): Promise<MessageOut[]> {
  const q = new URLSearchParams({ q: query });
  if (opts.start) q.set("start", opts.start);
  if (opts.end) q.set("end", opts.end);
  if (opts.limit) q.set("limit", String(opts.limit));
  return requestJson<MessageOut[]>(`/messages/search?${q.toString()}`);
}

export function searchMemory(query: string, limit = 5): Promise<MemoryOut[]> {
  const q = new URLSearchParams({ q: query, limit: String(limit) });
  return requestJson<MemoryOut[]>(`/memory/search?${q.toString()}`);
}

export function getSummaries(limit = 10): Promise<LongitudinalSummary[]> {
  return requestJson<LongitudinalSummary[]>(`/longitudinal/summaries?limit=${limit}`);
}

/** Latest weekly chapter. Resolves to null on 404 (none generated yet). */
export async function getLatestSummary(): Promise<LongitudinalSummary | null> {
  try {
    return await requestJson<LongitudinalSummary>("/longitudinal/latest");
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export function getCalendar(start?: string, end?: string): Promise<CalendarOut> {
  const q = new URLSearchParams();
  if (start) q.set("start", start);
  if (end) q.set("end", end);
  const qs = q.toString();
  return requestJson<CalendarOut>(`/calendar${qs ? `?${qs}` : ""}`);
}

export function getMuseum(): Promise<MuseumOut> {
  return requestJson<MuseumOut>("/museum");
}

/** Non-streamed full turn — also the fallback when the SSE stream fails. */
export function postChat(message: string, sessionId?: string): Promise<ChatResponse> {
  return requestJson<ChatResponse>("/chat", jsonPost({ message, session_id: sessionId }));
}

/** Synthesize speech. Throws (any non-200, incl. 503) so the caller can quietly stay text. */
export async function postVoice(
  text: string,
  conversationMode = "casual",
  voiceId?: string
): Promise<Blob> {
  const res = await fetch(
    `${BASE}/voice`,
    jsonPost({ text, conversation_mode: conversationMode, voice_id: voiceId })
  );
  if (!res.ok) throw new ApiError(res.status, `voice unavailable (${res.status})`);
  return res.blob();
}
