/*
 * The typed API client. Every call is same-origin against /api/* (Next rewrites to FastAPI).
 * JSON/blob endpoints live here; the SSE stream is read directly in useChatStream (Task 8).
 */
import type { TypingSignals } from "@/lib/chat/typingSignals";
import {
  ApiError,
  type CalendarOut,
  type ChatResponse,
  type Goal,
  type HomeOut,
  type IntegrityOut,
  type JobRunOut,
  type LongitudinalSummary,
  type MemoryAuditOut,
  type MemoryDeletion,
  type MemoryOut,
  type MessageOut,
  type MuseumOut,
  type OnboardingOut,
  type PersonDetailOut,
  type PersonOut,
  type ProactiveItem,
  type RelationshipOut,
  type SafetyEvent,
  type SessionOut,
  type SyncStatus,
  type ToolAction,
  type ToolConfirmation,
  type ToolResult,
  type TranscribeOut,
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

export function getGoals(status?: string): Promise<Goal[]> {
  return requestJson<Goal[]>(`/goals${status ? `?status=${encodeURIComponent(status)}` : ""}`);
}

export function getGoal(goalId: string): Promise<Goal> {
  return requestJson<Goal>(`/goals/${encodeURIComponent(goalId)}`);
}

export function createGoal(title: string, description?: string): Promise<Goal> {
  return requestJson<Goal>("/goals", jsonPost({ title, description }));
}

export function updateGoal(
  goalId: string,
  patch: { status?: string; progress_score?: number }
): Promise<Goal> {
  return requestJson<Goal>(`/goals/${encodeURIComponent(goalId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

export async function deleteGoal(goalId: string): Promise<void> {
  const res = await fetch(`${BASE}/goals/${encodeURIComponent(goalId)}`, { method: "DELETE" });
  if (!res.ok) throw new ApiError(res.status, `goal delete failed (${res.status})`);
}

export function getRelationship(): Promise<RelationshipOut> {
  return requestJson<RelationshipOut>("/relationship");
}

export function getPeople(): Promise<PersonOut[]> {
  return requestJson<PersonOut[]>("/people");
}

export function getPerson(personId: string): Promise<PersonDetailOut> {
  return requestJson<PersonDetailOut>(`/people/${encodeURIComponent(personId)}`);
}

export function getProactive(limit = 5): Promise<ProactiveItem[]> {
  return requestJson<ProactiveItem[]>(`/proactive?limit=${limit}`);
}

/** SC-5: call the moment a client actually shows a proactive item to the user, so the next reply
 *  can be attributed to it via ChatRequest.is_reply_to_proactive. */
export function markProactiveDelivered(itemId: string): Promise<{ item_id: string; status: string }> {
  return requestJson(`/proactive/${encodeURIComponent(itemId)}/delivered`, { method: "POST" });
}

/** One memory in full — the detail view behind an echo or a list entry. */
export function getMemory(memoryId: string): Promise<MemoryOut> {
  return requestJson<MemoryOut>(`/memory/${encodeURIComponent(memoryId)}`);
}

/** Readiness: is the database up? Nova's "awake / resting" pulse. */
export function getReady(): Promise<{ status: string }> {
  return requestJson<{ status: string }>("/health/ready");
}

export function getMemoryAudit(): Promise<MemoryAuditOut> {
  return requestJson<MemoryAuditOut>("/memory/audit");
}

export function getIntegrity(): Promise<IntegrityOut> {
  return requestJson<IntegrityOut>("/memory/integrity");
}

/** Layer-12 selective "forget" — content/embedding zeroed, row kept for proof. */
export function deleteMemory(memoryId: string): Promise<MemoryDeletion> {
  return requestJson<MemoryDeletion>(`/memory/${encodeURIComponent(memoryId)}`, { method: "DELETE" });
}

export function getSyncStatus(): Promise<SyncStatus> {
  return requestJson<SyncStatus>("/sync/status");
}

export function runJob(name: string): Promise<JobRunOut> {
  return requestJson<JobRunOut>(`/admin/jobs/${encodeURIComponent(name)}`, { method: "POST" });
}

export function getOnboarding(): Promise<OnboardingOut> {
  return requestJson<OnboardingOut>("/onboarding");
}

export function getSessions(): Promise<SessionOut[]> {
  return requestJson<SessionOut[]>("/sessions");
}

export function getPendingTools(): Promise<ToolConfirmation[]> {
  return requestJson<ToolConfirmation[]>("/tools/pending");
}

export function confirmTool(requestId: string): Promise<ToolResult> {
  return requestJson<ToolResult>(`/tools/confirm/${encodeURIComponent(requestId)}`, {
    method: "POST",
  });
}

export function denyTool(requestId: string): Promise<{ denied: string }> {
  return requestJson<{ denied: string }>(`/tools/deny/${encodeURIComponent(requestId)}`, {
    method: "POST",
  });
}

export function getToolHistory(): Promise<ToolAction[]> {
  return requestJson<ToolAction[]>("/tools/history");
}

export function undoTool(actionId: string): Promise<{ undone: boolean }> {
  return requestJson<{ undone: boolean }>(`/tools/undo/${encodeURIComponent(actionId)}`, {
    method: "POST",
  });
}

export function getSafetyEvents(limit = 20): Promise<SafetyEvent[]> {
  return requestJson<SafetyEvent[]>(`/safety/events?limit=${limit}`);
}

export function getBookmarks(category?: string): Promise<MessageOut[]> {
  return requestJson<MessageOut[]>(
    `/bookmarks${category ? `?category=${encodeURIComponent(category)}` : ""}`
  );
}

export function getMilestones(): Promise<MessageOut[]> {
  return requestJson<MessageOut[]>("/milestones");
}

export function setBookmark(messageId: string, category?: string): Promise<MessageOut> {
  return requestJson<MessageOut>(`/messages/${messageId}/bookmark`, jsonPost({ category }));
}

export function removeBookmark(messageId: string): Promise<MessageOut> {
  return requestJson<MessageOut>(`/messages/${messageId}/bookmark`, { method: "DELETE" });
}

export function setMilestone(messageId: string, label?: string): Promise<MessageOut> {
  return requestJson<MessageOut>(`/messages/${messageId}/milestone`, jsonPost({ label }));
}

export function removeMilestone(messageId: string): Promise<MessageOut> {
  return requestJson<MessageOut>(`/messages/${messageId}/milestone`, { method: "DELETE" });
}

/** Non-streamed full turn — also the fallback when the SSE stream fails. */
export function postChat(
  message: string,
  sessionId?: string,
  signals?: TypingSignals
): Promise<ChatResponse> {
  return requestJson<ChatResponse>("/chat", jsonPost({ message, session_id: sessionId, ...signals }));
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

/** Upload a recorded utterance for transcription. Throws (any non-200, incl. 503) so the caller
 * can fall back to letting the user type instead. */
export async function transcribeVoice(blob: Blob): Promise<TranscribeOut> {
  const form = new FormData();
  form.append("file", blob, "clip.webm");
  const res = await fetch(`${BASE}/voice/transcribe`, { method: "POST", body: form });
  if (!res.ok) throw new ApiError(res.status, `transcription unavailable (${res.status})`);
  return (await res.json()) as TranscribeOut;
}
