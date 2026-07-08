/*
 * API response types, transcribed from docs/API_REFERENCE.md. The backend is the source of truth;
 * when it changes, mirror it here. All requests go same-origin through /api/* (Next rewrites).
 */

/** A memory Nova recalled while writing a reply — the one permitted ambient element. */
export type Echo = {
  summary: string;
  when: string;
  created_at: string | null;
};

export type ConversationMode =
  | "casual"
  | "emotional_support"
  | "crisis"
  | "celebration"
  | "technical_discussion"
  | "goal_planning"
  | "social_coaching"
  | "life_review";

export type CognitiveSystem = "system1" | "system2";

/** GET /home — the Digital Desk. */
export type HomeOut = {
  greeting: string;
  current_chapter: string | null;
  relationship_stage: string;
  last_interaction_at: string | null;
  weather: string;
  active_goals: number;
  top_proactive: string | null;
  cold_start_active: boolean;
  message_count: number;
};

/** One persisted turn-half. GET /messages, /messages/search, bookmark/milestone mutations. */
export type MessageOut = {
  message_id: string;
  cursor: number;
  role: "user" | "nova";
  content: string;
  created_at: string | null;
  conversation_mode: ConversationMode | null;
  crisis_active: boolean;
  tool_invoked: boolean;
  echoes: Echo[];
  bookmarked: boolean;
  bookmark_category: string | null;
  is_milestone: boolean;
  milestone_label: string | null;
};

/** GET /memory/search — semantic episodic hits. */
export type MemoryOut = {
  memory_id: string;
  summary: string;
  importance: number;
  created_at: string | null;
  topic_tags: string[];
};

/** POST /chat — the non-streamed full turn (also the streaming fallback). */
export type ChatResponse = {
  response: string;
  conversation_mode: ConversationMode;
  cognitive_system: CognitiveSystem;
  crisis_active: boolean;
  crisis_tier: string | null;
  refined: boolean;
  tool_invoked: boolean;
  confabulation_guard: boolean;
  echoes: Echo[];
  session_id: string;
};

/** POST /chat/stream — the `meta` frame payload. */
export type ChatMeta = {
  session_id: string;
  conversation_mode: ConversationMode;
  cognitive_system: CognitiveSystem;
  crisis_active: boolean;
  refined: boolean;
  confabulation_guard: boolean;
};

/** POST /chat/stream — a `token` frame payload. Concatenated tokens == the delivered text. */
export type ChatTokenFrame = {
  token: string;
  delay_ms: number;
};

/** POST /chat/stream — the `done` frame payload (carries the final echoes). */
export type ChatDone = {
  session_id: string;
  conversation_mode: ConversationMode;
  cognitive_system: CognitiveSystem;
  crisis_active: boolean;
  refined: boolean;
  echoes?: Echo[];
};

/** GET /longitudinal/summaries, /longitudinal/latest — a week's chapter (Layer 10). */
export type LongitudinalSummary = {
  summary_id: string;
  week_start_date: string | null;
  week_end_date: string | null;
  session_count: number;
  dominant_theme: string;
  week_narrative: string;
};

/** GET /calendar — per-day message counts for a heatmap. */
export type CalendarOut = {
  start: string;
  end: string;
  days: Record<string, number>;
};

/** GET /museum — "firsts" derived from the log + milestones + goals. */
export type MuseumEntry = { label: string; content: string; when: string | null };
export type MuseumOut = { entries: MuseumEntry[] };

/** A thrown API error carrying the HTTP status and backend `detail`. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}
