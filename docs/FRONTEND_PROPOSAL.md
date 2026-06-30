# Nova AI — Frontend Architecture & UX Proposal

This document outlines the proposed frontend architecture and UX paradigms for Nova AI, designed to complement its 13-layer longitudinal cognitive backend.

The primary goal of the frontend is **not to build a chat interface**, but to build a **persistent companion surface** that correctly renders Nova's micro-interactions (Layer 9), captures implicit behavioral signals (Layer 1), and visualizes longitudinal growth (Layer 10).

## 1. Technical Stack

Given the `api/main.py` CORS configuration anticipating `localhost:3000` and the need for robust state management and WebSocket streaming, the recommended stack is:

- **Framework:** Next.js (App Router, React 18+)
- **State Management:** Zustand (for transient UI state, typing indicators, tool statuses) + React Query (for longitudinal/REST data like Goals and Memories).
- **Styling:** Tailwind CSS + Framer Motion (for fluid micro-interactions and transitions).
- **Communication:**
  - **WebSockets (`/chat/stream`):** Primary realtime channel. Needed to consume streaming events for Layer 9 (typing simulations, self-edits, thinking pauses) and deliver real-time voice synthesis (Kokoro TTS).
  - **REST:** For auth, fetching Layer 10 (Life Narrative), Layer 7 (Goals), and Layer 12 (Sync/Privacy settings).
- **Audio/Voice:** Web Audio API for continuous voice synthesis playback (SSML-driven).

## 2. Core UX Paradigms

### A. The "Living Surface" vs. The "Chat History"
Standard chatbots treat past messages as dead text. For Nova, the frontend should reflect its memory and longitudinal awareness.
- **Ambient Presence:** The UI should visually indicate Nova's "background state" (Layer 3). Subtle gradient shifts or status indicators could reflect if Nova is in `casual`, `emotional_support`, or `goal_planning` mode.
- **Proactive Surfacing:** When Layer 6 (Proactivity) or Layer 10 (Retrospective) pushes an event, it shouldn't just be a chat bubble. It could be a dedicated "notification card" or a visual element that feels distinct from user-prompted responses.

### B. Layer 9: Micro-Interactions Execution
The frontend must perfectly execute the orchestration directed by Layer 9:
- **Thinking Pauses:** Render a distinct visual state when Nova is "processing" or "reflecting," avoiding the standard spinning loader.
- **Typing Simulation:** Nova's backend sends staggered typing events. The frontend must render these at the exact cadence dictated by the backend to simulate human-like pacing.
- **Self-Editing:** The frontend needs a text-rendering component capable of handling backspace/overwrite events if Layer 9 simulates a "rethought" sentence.
- **Crisis Mode Override (Layer 11):** If the backend enters `crisis_mode_active=True`, the frontend must immediately suppress all typing delays and micro-interactions, instantly rendering the pure prose block provided by the Escalation Protocol.

### C. Layer 1: Implicit Signal Collection
The frontend is the sensor for Layer 1's input perception:
- **Typing Metrics:** The client should track the user's keystroke cadence, pause durations, and backspace counts, sending these as lightweight metadata with the message payload.
- **Time/Circadian Context:** The frontend must enforce the delivery of local timezone data and session-gap timing so Layer 1 can accurately apply fuzzy temporal labels.

## 3. Key Views & Components

### 1. The Interaction Canvas (Primary View)
- **Input Area:** Not just a text box. It needs a voice-input toggle (dictation) and must silently track behavioral metrics (deletions, latency) before submission.
- **Stream Renderer:** A highly optimized message list that can handle real-time chunked updates, inline tool-use confirmations (Layer 8 AUTO/SOFT/HARD gates), and audio playback synchronization.

### 2. The Longitudinal Dashboard (Layer 10 & Layer 7)
- **Life Calendar & Narrative Arcs:** A visual timeline separate from the chat that displays Weekly Summaries, major Life Chapters, and tracked Goals.
- **Progress Visualization:** Beautiful, non-intrusive charts or milestones reflecting Goal extraction and progress (Layer 7).

### 3. The Onboarding Overlay (Layer 13)
- **Cold Start Experience:** While Layer 13 governs the progressive elicitation, the frontend should render this as a seamless, natural conversation rather than a rigid form. Subtle UI hints can show trust/feature unlocking over the first 14 sessions.

### 4. Privacy & Sync Hub (Layer 12)
- **Zero-Knowledge Controls:** A dedicated settings area where the user can manage their Local Device Key, perform selective deletions (Triggering Layer 12's cascade removal), and view the tamper-evident Memory Audit log.

## 4. Integration Blueprint

1. **WebSocket Event Schema:**
   The Next.js client will need a robust WebSocket listener that switches based on event types: `token`, `thinking_start`, `typing_start`, `self_edit`, `audio_chunk`, `tool_gate_prompt`.
2. **Audio Pipeline:**
   Audio chunks sent from the backend Kokoro TTS must be queued and played seamlessly in the browser.
3. **Local-First Caching:**
   To respect privacy, local data like the User World Model (if fetched for UI reasons) should rely on secure client-side storage (e.g., IndexedDB) and never be synced via third-party telemetry.

## Summary

This frontend proposal aims to faithfully manifest the 13-layer depth of Nova AI. By leveraging Next.js, WebSockets, and precise UI components tailored to Layer 9 and Layer 1, the frontend will shift the experience from interacting with a tool to building a persistent, emotionally intelligent relationship.