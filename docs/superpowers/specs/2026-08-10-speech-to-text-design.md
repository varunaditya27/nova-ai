# Speech-to-Text (Dictation) — Design Spec

**Date:** 2026-08-10
**Status:** Approved, implementing
**Scope:** Push-to-talk voice input that transcribes into the chat composer as editable text.
Fully offline (local faster-whisper), matching this session's Groq-removal decision. WebSocket is
explicitly out of scope — see §6.

---

## 1. Motivation

`/voice` (Kokoro) is TTS output only; there is no way to speak a message in. This closes that gap
with the simplest UX that's actually useful: hold a mic button, speak, release, see the transcript
land in the composer to review/edit before sending as a normal text message — the same mental
model as voice dictation in any messaging app.

This is a different feature from Layer 1's `VoiceBackend` Protocol
(`backend/layer1_input/multimodal_normalizer.py`) — that path is for attaching a voice *note* as a
distinct input modality Nova perceives specially (with its own confidence/degradation handling
feeding the cognitive pipeline). It needs a message-attachments system that doesn't exist yet
(`ChatRequest` has no attachment field — `DEFERRED_WORK.md` #2, separately deferred). Wiring
`NormalizerBackends.voice` now would have zero caller. Not attempted here — see §6.

## 2. Design decisions

| Decision | Choice |
|---|---|
| Recording model | Push-to-talk: hold to record (client-side `MediaRecorder`), release to send the whole utterance as one blob. No live/streaming partial transcription — no WebSocket needed. |
| Transcription engine | faster-whisper, `small` model, fully local. |
| Deployment | Own Docker service (`stt`), matching Kokoro's exact pattern: thin Dockerfile wrapping a maintained upstream image (`fedirz/faster-whisper-server`, OpenAI-Whisper-API-compatible `/v1/audio/transcriptions`), loopback-bound port. **Verify the real image's request/response shape against a live container during implementation** — this is exactly the class of assumption that needs a live check, not just reading the image's README. |
| Integration point | Standalone endpoint, not the Layer-1 attachment path (see §1). |
| Failure mode | 503, matching `/voice`'s existing degrade-to-text(here: degrade-to-typing) contract — never blocks the user from typing instead. |
| Config | `config.stt.endpoint` (`STT_URL` env, default `http://stt:8880`), `config.stt.model` (`small`), mirroring the existing `tts:` block shape exactly. |

## 3. Components

### 3.1 `backend/layer9_output/stt_backends/` (new package, mirrors `tts_backends/`)
- `base_backend.py`: `STTBackend` ABC — `transcribe(audio_bytes: bytes, mime_type: str) -> TranscriptResult`, `health_check() -> bool`.
- `whisper_backend.py`: `WhisperBackend(STTBackend)` — injected `request_fn` (same httpx-adapter pattern as `KokoroBackend`), POSTs multipart audio to the faster-whisper-server endpoint, maps its response to `TranscriptResult(ok, transcript, confidence, language, error)`.
- `backend/layer9_output/schemas.py`: add `TranscriptResult` dataclass alongside the existing `AudioResult`.

### 3.2 `api/state.py`
- `build_stt_backend(config)`: mirrors `build_voice_backend` exactly — same httpx-adapter closure, returns `None` (graceful) if httpx is unavailable.
- `AppState.stt_backend: Any = None`.

### 3.3 `api/routes/voice.py` (extend, not a new file — same route module as TTS)
- `POST /voice/transcribe`: `UploadFile` (multipart audio) → calls `state.stt_backend.transcribe(...)` → `{transcript, confidence, language}`. 503 if backend unavailable or transcription fails, matching `synthesize_voice`'s existing error handling exactly.
- `api/schemas.py`: `TranscribeOut` (`transcript: str`, `confidence: float`, `language: str | None`).

### 3.4 `docker/`
- `stt.Dockerfile`: thin wrapper, `FROM fedirz/faster-whisper-server:latest-cpu` (or the exact tag verified during implementation), model pinned to `small` via its config/env.
- `docker-compose.yml`: new `stt` service, loopback-bound port (e.g. `127.0.0.1:8881:8000`, exact port TBD by the image), same `nova-network`.
- `docker/.env.example`: `STT_URL=http://stt:8880` alongside the existing `OLLAMA_BASE_URL`/`KOKORO_BASE_URL` entries.

### 3.5 Frontend
- `lib/api/client.ts`: `transcribeVoice(blob: Blob): Promise<TranscribeOut>` — multipart POST to `/voice/transcribe`.
- `lib/hooks/useDictation.ts` (new): wraps `MediaRecorder` — `startRecording()`/`stopRecording()`, returns `{recording, transcribing, transcript, error}`; on stop, uploads the recorded blob and resolves the transcript.
- `components/chat/Composer.tsx`: a mic button (mirrors `VoiceButton`'s visual language — icon-only, subtle) — press-and-hold triggers `startRecording`, release triggers `stopRecording`; on a successful transcript, appends it into the composer's text value (does not auto-send).
- Permissions: standard browser mic-permission prompt on first use; if denied or `MediaRecorder`/`getUserMedia` is unsupported, the mic button doesn't render (progressive enhancement, matches `VoiceButton`'s silent-fail philosophy) rather than showing a broken control.

## 4. Testing
- `tests/unit/backend/layer9_output/test_whisper_backend.py`: injected fake `request_fn`, success/failure/malformed-response paths — mirrors `test_kokoro_backend.py`'s existing structure exactly.
- `tests/unit/api/test_routes_voice.py` (extend): `POST /voice/transcribe` with a stubbed backend on `AppState` — success, 503-on-unavailable, 503-on-failure.
- Live verification (required before calling this done, not optional): build and run the `stt` Docker service for real, confirm the actual multipart request/response shape matches what `WhisperBackend` assumes, and drive one real press-and-hold-to-transcript round trip through the running frontend.

## 5. Success criteria
1. Holding the mic button and speaking, then releasing, puts real transcribed text in the composer.
2. STT backend down → mic button silently doesn't impede typing (503 handled, no broken UI state).
3. Fully offline — zero calls to any cloud STT API.

## 6. Non-goals (this round)
- **WebSocket / live streaming transcription.** Push-to-talk records client-side and uploads once;
  no persistent duplex connection is needed. Documented in `frontend/DEFERRED_WORK.md` #5 with what
  would actually justify building it: live partial captions (text appearing word-by-word while
  speaking) or a real mid-turn-cancel feature for slow System-2 replies — neither exists as a
  concrete need today.
- **Layer-1 voice-attachment wiring** (`NormalizerBackends.voice`) — blocked on the attachments
  system (`DEFERRED_WORK.md` #2), not this feature. `WhisperBackend` could later be reused there
  once attachments exist, rather than building a second transcription engine.
- Multi-language UI, voice commands, always-listening/wake-word — out of scope, no request for them.
