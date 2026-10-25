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
  name: string | null;
};

/** One persisted turn-half. GET /messages, /messages/search, bookmark/milestone mutations. */
export type MessageOut = {
  message_id: string;
  cursor: number;
  role: "user" | "nova";
  content: string;
  created_at: string | null;
  session_key: string;
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

/** GET/POST /goals (Layer 7). */
export type Goal = {
  goal_id: string;
  title: string;
  status: string;
  progress_score: number;
  description: string;
  deadline: string | null;
  deadline_description: string | null;
  milestones: { title: string; target_date: string | null; status: string }[];
  habits: {
    title: string;
    frequency: string;
    current_streak: number;
    best_streak: number;
    total_check_ins: number;
  }[];
};

/** GET /relationship (Layer 4/5) — stage + learned communication-style calibration. */
export type RelationshipOut = {
  stage: string;
  total_sessions: number;
  total_messages_exchanged: number;
  tie_strength: number;
  trust_score: number;
  formality_preference: number;
  response_length_preference: number;
  question_tolerance: number;
  unsolicited_advice_tolerance: number;
};

/** GET /people (Layer 5) — a person in Nova's social graph. */
export type PersonOut = {
  person_id: string;
  display_name: string;
  relationship_type: string;
  relationship_valence: number;
  valence_trend: number;
  interaction_frequency: string;
  is_support_source: boolean;
  active_conflict: boolean;
  mention_count: number;
  last_mentioned: string | null;
};

export type SocialEvent = {
  event_id: string;
  event_type: string;
  summary: string;
  event_valence: number;
  event_timestamp: string | null;
  is_resolved: boolean;
};

export type SocialPattern = {
  pattern_id: string;
  pattern_type: string;
  plain_language_description: string;
  pattern_confidence: number;
  is_active: boolean;
};

/** GET /people/{id} — one person's full record + timeline. */
export type PersonDetailOut = PersonOut & {
  recent_events: SocialEvent[];
  active_patterns: SocialPattern[];
};

/** GET /proactive (Layer 6) — a thought Nova is holding. */
export type ProactiveItem = {
  item_id: string;
  item_type: string;
  status: string;
  content_basis: string;
  /** The real SC-4-generated delivery text — what Nova would actually say. Empty until the
   *  background job has produced one; render this, never content_basis (an internal fragment). */
  message: string;
  current_priority: number;
};

/** One `item` event from GET /proactive/stream. */
export type ProactiveStreamItem = {
  item_id: string;
  item_type: string;
  message: string;
  current_priority: number;
};

/** GET /memory/audit (Layer 2). */
export type SemanticMemory = { memory_id: string; statement: string; confidence: number };
export type MemoryAuditOut = { episodic: MemoryOut[]; semantic: SemanticMemory[] };

/** GET /memory/integrity — both tamper-evident hash chains. */
export type IntegrityOut = {
  status: "INTACT" | "TAMPER_DETECTED";
  audit_chain_ok: boolean;
  privacy_chain_ok: boolean;
  safety_chain_ok: boolean;
};

/** DELETE /memory/{id} — a signed "forget". */
export type MemoryDeletion = {
  deleted: number;
  memory_id: string;
  certificate: string;
  cascade: string;
};

/** GET /sync/status (Layer 12 zero-knowledge relay). */
export type SyncStatus = {
  total_deltas: number;
  by_device: Record<string, number>;
  latest_cursor: number;
};

/** POST /admin/jobs/{name} — run a background job on demand. */
export type JobRunOut = { job: string; result: Record<string, unknown> };

/** GET /tools/pending (Layer 8) — a SOFT/HARD action awaiting confirmation. */
export type ToolConfirmation = {
  request_id: string;
  tool_name: string;
  action_type: string;
  action_description: string;
  tier: string;
  reversible: boolean;
};

/** POST /tools/confirm/{id} — the executed action's outcome. */
export type ToolResult = {
  ok: boolean;
  tool_name: string;
  operation: string;
  outcome: string;
  result_summary: string;
  error_message: string | null;
};

/** GET /tools/history — durable audit of executed actions. */
export type ToolAction = {
  action_id: string;
  tool_name: string;
  operation: string;
  action_type: string;
  outcome: string;
  result_summary: string;
  undone: boolean;
};

/** GET /safety/events (Layer 11) — a logged moment of concern. */
export type SafetyEvent = {
  tier: string;
  confidence: number;
  detected_at: string | null;
  signal_types: string[];
};

/** GET /onboarding (Layer 13). */
export type OnboardingOut = { cold_start_active: boolean; session_index: number };

/** GET /sessions. */
export type SessionOut = { session_key: string; turn_count: number };

/** POST /voice/transcribe — a dictated utterance transcribed locally. */
export type TranscribeOut = {
  transcript: string;
  confidence: number;
  language: string | null;
};

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
