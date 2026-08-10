# Speech-to-Text (Dictation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push-to-talk voice input — hold a mic button, speak, release, get a real transcript in the
chat composer to review/edit before sending. Fully offline (local faster-whisper).

**Architecture:** A new `STTBackend` ABC (mirrors the existing `TTSBackend` pattern exactly) with a
`WhisperBackend` implementation that POSTs audio to a local faster-whisper HTTP service (its own
Docker container, matching Kokoro's exact pattern). A new `POST /voice/transcribe` endpoint (same
route module as the existing TTS `/voice` route) exposes it. Frontend records audio client-side via
`MediaRecorder`, uploads the whole clip on release, and fills the composer with the returned text.

**Tech Stack:** faster-whisper (`small` model) via the `fedirz/faster-whisper-server` Docker image,
FastAPI (`UploadFile` multipart), `httpx` (server-side transport), browser `MediaRecorder` API.

## Global Constraints

- Fully offline — no cloud STT API, matching this session's Groq-removal decision.
- Backend unavailable/failure → `503`, never blocks typing (matches `/voice`'s existing
  degrade-to-text contract exactly).
- No WebSocket — client records the whole utterance locally, uploads once. See
  `docs/superpowers/specs/2026-08-10-speech-to-text-design.md` §6 for why.
- **Verify the real `fedirz/faster-whisper-server` request/response shape and port against a live
  running container before finalizing `WhisperBackend`** — Task 2 Step 1 depends on this and must
  not be written from assumption alone.
- Mic button is progressive enhancement: if `navigator.mediaDevices`/`MediaRecorder` is unsupported
  or permission is denied, it doesn't render / silently no-ops — never a broken control.

---

### Task 1: `STTBackend` ABC + `TranscriptResult` schema

**Files:**
- Create: `backend/layer9_output/stt_backends/__init__.py`
- Create: `backend/layer9_output/stt_backends/base_backend.py`
- Modify: `backend/layer9_output/schemas.py` (append after `AudioResult`, ~line 197)

**Interfaces:**
- Produces: `TranscriptResult` dataclass, `STTBackend` ABC with `transcribe(audio_bytes: bytes,
  mime_type: str) -> TranscriptResult` and `health_check() -> bool` — consumed by Task 2.

- [ ] **Step 1: Add `TranscriptResult` to schemas**

In `backend/layer9_output/schemas.py`, after the `AudioResult` dataclass:

```python
@dataclass
class TranscriptResult:
    transcript: str = ""
    confidence: float = 0.0
    language: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
```

- [ ] **Step 2: Create the package + ABC**

```python
# backend/layer9_output/stt_backends/__init__.py
```
(empty — package marker)

```python
# backend/layer9_output/stt_backends/base_backend.py
"""Base STT backend interface, sibling to tts_backends/base_backend.py.

Abstract base for all speech-to-text providers so engine selection is transparent to callers.
Subclasses implement ``transcribe``; the base provides a safe default health-check.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.layer9_output.schemas import TranscriptResult


class STTBackend(ABC):
    """Uniform interface the dictation endpoint calls every STT provider through."""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> TranscriptResult:
        """Transcribe ``audio_bytes`` to text, returning a TranscriptResult (ok flag + text/error)."""

    def health_check(self) -> bool:
        return True
```

- [ ] **Step 3: Verify it imports cleanly**

Run: `.venv/bin/python -c "from backend.layer9_output.stt_backends.base_backend import STTBackend; from backend.layer9_output.schemas import TranscriptResult; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/layer9_output/stt_backends/ backend/layer9_output/schemas.py
git commit -m "Add STTBackend ABC and TranscriptResult schema"
```

---

### Task 2: Stand up the faster-whisper Docker service and verify its real API

**Files:**
- Create: `docker/stt.Dockerfile`
- Modify: `docker/docker-compose.yml` (add `stt` service after `kokoro`)
- Modify: `docker/.env.example` (add `STT_URL` after `KOKORO_BASE_URL`)

This task is verification-first: the exact request/response shape of the upstream image must be
confirmed against a real running container before Task 3 writes `WhisperBackend` against it.

- [ ] **Step 1: Write the Dockerfile**

```dockerfile
# faster-whisper STT server — OpenAI-Whisper-API-compatible transcription on :8000 (used by
# Layer 9 speech-to-text). Wraps the upstream image so it's pinned and buildable from this repo,
# matching kokoro.Dockerfile's pattern exactly.
FROM fedirz/faster-whisper-server:latest-cpu

ENV WHISPER__MODEL=Systran/faster-whisper-small

EXPOSE 8000
```

- [ ] **Step 2: Add the compose service**

In `docker/docker-compose.yml`, after the `kokoro:` service block:

```yaml
  stt:
    build:
      context: ..
      dockerfile: docker/stt.Dockerfile
    ports: ["127.0.0.1:8881:8000"]
    networks: [nova-network]
```

- [ ] **Step 3: Add the env var**

In `docker/.env.example`, after the `KOKORO_BASE_URL` line:

```
# faster-whisper (STT)
STT_URL=http://stt:8880
```

(Note: the container's internal port is `8000`, matching the compose port mapping above — `STT_URL`
here is for reference/documentation of the intended external-facing env var name; the actual value
consumed by the app talks to the service on the docker network at its internal port. Reconcile the
exact URL/port in Task 4 once the running container is confirmed live in Step 4 below.)

- [ ] **Step 4: Build and run the real container, verify its actual API**

```bash
docker compose -f docker/docker-compose.yml build stt
docker compose -f docker/docker-compose.yml up -d stt
sleep 5
curl -s http://127.0.0.1:8881/health
```

Record the actual response. Then send a real test file:

```bash
curl -s -X POST http://127.0.0.1:8881/v1/audio/transcriptions \
  -F "file=@/usr/share/sounds/alsa/Front_Center.wav" \
  -F "model=Systran/faster-whisper-small"
```

(If no test WAV is available on the machine, generate one: `ffmpeg -f lavfi -i "sine=frequency=440:duration=1" -ar 16000 /tmp/test.wav` and use that path instead — the point is confirming the *shape* of the JSON response, not the transcript content of silence/a tone.)

**Record the exact response JSON shape here before proceeding to Task 3** — this determines exactly
how `WhisperBackend._parse_response` (Task 3) must map fields. The `fedirz/faster-whisper-server`
image is OpenAI-compatible, so the expected default shape is `{"text": "..."}` for
`response_format=json` (or plain text for the default `response_format`), but this must be
confirmed against the real running container, not assumed.

- [ ] **Step 5: Stop the container (Task 3 will restart it as needed)**

```bash
docker compose -f docker/docker-compose.yml stop stt
```

- [ ] **Step 6: Commit**

```bash
git add docker/stt.Dockerfile docker/docker-compose.yml docker/.env.example
git commit -m "Add stt Docker service (faster-whisper, small model)"
```

---

### Task 3: `WhisperBackend`

**Files:**
- Create: `backend/layer9_output/stt_backends/whisper_backend.py`
- Create: `tests/unit/test_whisper_backend.py`

**Interfaces:**
- Consumes: `STTBackend`, `TranscriptResult` (Task 1); the real response shape confirmed in Task 2
  Step 4.
- Produces: `WhisperBackend(STTBackend)` with constructor `(endpoint: str, model: str = "small",
  request_fn: Optional[Callable] = None)` and `.transcribe(audio_bytes, mime_type) ->
  TranscriptResult` — consumed by Task 4.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the STT WhisperBackend, mirroring tests/unit/test_kokoro_backend.py's structure."""

from backend.layer9_output.stt_backends.base_backend import STTBackend
from backend.layer9_output.stt_backends.whisper_backend import WhisperBackend


class _Resp:
    def __init__(self, ok=True, json_data=None, status_code=200):
        self.ok, self._json, self.status_code = ok, json_data or {}, status_code

    def json(self):
        return self._json


def _recording_client(resp=None, raises=False):
    calls = []

    def request_fn(method, url, files=None, data=None):
        calls.append({"method": method, "url": url, "files": files, "data": data})
        if raises:
            raise ConnectionError("stt service unreachable")
        return resp or _Resp()
    return request_fn, calls


def test_whisper_is_an_stt_backend():
    assert isinstance(WhisperBackend(endpoint="http://x", request_fn=lambda *a, **k: _Resp()), STTBackend)


def test_transcribe_returns_text_on_success():
    fn, _ = _recording_client(_Resp(json_data={"text": "hello nova"}))
    res = WhisperBackend(endpoint="http://x", request_fn=fn).transcribe(b"AUDIO", "audio/webm")
    assert res.ok is True
    assert res.transcript == "hello nova"


def test_transcribe_sends_audio_as_multipart():
    fn, calls = _recording_client(_Resp(json_data={"text": "hi"}))
    WhisperBackend(endpoint="http://x", model="small", request_fn=fn).transcribe(b"AUDIO", "audio/webm")
    assert calls[-1]["url"].endswith("/v1/audio/transcriptions")
    assert calls[-1]["data"]["model"] == "small"
    assert calls[-1]["files"]["file"][1] == b"AUDIO"


def test_connection_error_is_graceful():
    fn, _ = _recording_client(raises=True)
    res = WhisperBackend(endpoint="http://x", request_fn=fn).transcribe(b"AUDIO", "audio/webm")
    assert res.ok is False and res.error


def test_no_client_configured_fails_gracefully():
    res = WhisperBackend(endpoint="http://x", request_fn=None).transcribe(b"AUDIO", "audio/webm")
    assert res.ok is False


def test_non_ok_status_is_graceful():
    fn, _ = _recording_client(_Resp(ok=False, status_code=500))
    res = WhisperBackend(endpoint="http://x", request_fn=fn).transcribe(b"AUDIO", "audio/webm")
    assert res.ok is False


def test_health_check_true_when_reachable():
    fn, _ = _recording_client(_Resp(ok=True))
    assert WhisperBackend(endpoint="http://x", request_fn=fn).health_check() is True


def test_health_check_false_when_unreachable():
    fn, _ = _recording_client(raises=True)
    assert WhisperBackend(endpoint="http://x", request_fn=fn).health_check() is False
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/unit/test_whisper_backend.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.layer9_output.stt_backends.whisper_backend'`

- [ ] **Step 3: Write `WhisperBackend`**

Write the implementation using the exact response shape confirmed live in Task 2 Step 4. The
skeleton below assumes the OpenAI-compatible `{"text": "..."}` JSON shape — **adjust the field
access in `transcribe()` to match whatever Task 2 Step 4 actually recorded** before considering this
step done:

```python
"""faster-whisper STT backend (own Docker service, matching tts_backends/kokoro_backend.py's
exact request-injection pattern so this stays fully testable offline).
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer9_output.schemas import TranscriptResult
from backend.layer9_output.stt_backends.base_backend import STTBackend


class WhisperBackend(STTBackend):
    def __init__(
        self,
        endpoint: str = "http://localhost:8881",
        model: str = "small",
        request_fn: Optional[Callable] = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self._request_fn = request_fn

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> TranscriptResult:
        if self._request_fn is None:
            return TranscriptResult(ok=False, error="no STT transport configured")
        files = {"file": ("audio", audio_bytes, mime_type)}
        data = {"model": self.model}
        try:
            resp = self._request_fn(
                "POST", f"{self.endpoint}/v1/audio/transcriptions", files=files, data=data)
        except Exception as exc:  # transport/connection error → graceful fallback
            return TranscriptResult(ok=False, error=f"stt request failed: {exc}")
        if not getattr(resp, "ok", False):
            return TranscriptResult(ok=False, error=f"stt status {getattr(resp, 'status_code', '?')}")
        try:
            body = resp.json()
        except Exception:
            return TranscriptResult(ok=False, error="stt returned a non-JSON response")
        return TranscriptResult(transcript=body.get("text", ""), language=body.get("language"),
                                confidence=1.0, ok=True)

    def health_check(self) -> bool:
        if self._request_fn is None:
            return False
        try:
            resp = self._request_fn("GET", f"{self.endpoint}/health")
        except Exception:
            return False
        return bool(getattr(resp, "ok", False))
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/unit/test_whisper_backend.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/layer9_output/stt_backends/whisper_backend.py tests/unit/test_whisper_backend.py
git commit -m "Add WhisperBackend (faster-whisper STT client)"
```

---

### Task 4: `AppState.stt_backend` + `build_stt_backend`

**Files:**
- Modify: `api/state.py`

**Interfaces:**
- Consumes: `WhisperBackend` (Task 3).
- Produces: `AppState.stt_backend: Any = None` field; `build_stt_backend(config: dict) ->
  Optional[WhisperBackend]` — consumed by Task 6.

- [ ] **Step 1: Add the field to `AppState`**

In the `AppState` dataclass, after `voice_backend: Any = None`:

```python
    stt_backend: Any = None
```

- [ ] **Step 2: Add `build_stt_backend`, mirroring `build_voice_backend` exactly**

Immediately after `build_voice_backend`'s function body (before `def build_tool_manager`):

```python
def build_stt_backend(config: dict):
    """faster-whisper STT backend (Layer-9) with a real httpx transport, or None if httpx is
    unavailable. Adapts an httpx response to the `.ok/.status_code/.json()` shape the backend
    expects; any connection error degrades to a non-ok TranscriptResult inside the backend."""
    from types import SimpleNamespace
    try:
        import httpx
    except Exception:
        logger.warning("httpx unavailable; speech-to-text disabled")
        return None
    from backend.layer9_output.stt_backends.whisper_backend import WhisperBackend

    stt = config.get("stt", {}) or {}
    endpoint = stt.get("endpoint") or "http://localhost:8881"

    def _request(method, url, files=None, data=None):
        with httpx.Client(timeout=30.0) as client:
            if method == "POST":
                r = client.post(url, files=files, data=data)
            else:
                r = client.get(url)
        return SimpleNamespace(ok=r.is_success, status_code=r.status_code,
                               json=r.json)

    return WhisperBackend(endpoint=endpoint, model=stt.get("model", "small"), request_fn=_request)
```

- [ ] **Step 3: Wire it into `build_app_state`**

Find the `AppState(` construction call near the end of `build_app_state` (it currently passes
`voice_backend=build_voice_backend(config), stm_store=stm_store)`); add `stt_backend`:

```python
        voice_backend=build_voice_backend(config), stt_backend=build_stt_backend(config),
        stm_store=stm_store)
```

- [ ] **Step 4: Verify it imports cleanly**

Run: `.venv/bin/python -c "from api.state import build_stt_backend, AppState; print(AppState.__dataclass_fields__['stt_backend'])"`
Expected: prints the dataclass field, no error.

- [ ] **Step 5: Commit**

```bash
git add api/state.py
git commit -m "Wire WhisperBackend into AppState via build_stt_backend"
```

---

### Task 5: `config/defaults.yaml` STT block

**Files:**
- Modify: `config/defaults.yaml`

**Interfaces:** None new — read by `build_stt_backend` (Task 4) via `config.get("stt", {})`.

- [ ] **Step 1: Add the block**

After the `tts:` block:

```yaml
stt:                          # Layer-9 speech-to-text (faster-whisper, OpenAI-compatible)
  endpoint: ${STT_URL:-http://stt:8880}
  model: small
```

- [ ] **Step 2: Verify config loads cleanly**

Run: `.venv/bin/python -c "from config import load_config; print(load_config()['stt'])"`
Expected: `{'endpoint': 'http://stt:8880', 'model': 'small'}`

- [ ] **Step 3: Commit**

```bash
git add config/defaults.yaml
git commit -m "Add stt config block"
```

---

### Task 6: `POST /voice/transcribe` route

**Files:**
- Modify: `api/schemas.py` (append `TranscribeOut` after `VoiceRequest`)
- Modify: `api/routes/voice.py` (add the new endpoint)
- Modify: `tests/unit/api/test_routes_voice.py` (add transcribe tests)

**Interfaces:**
- Consumes: `AppState.stt_backend` (Task 4), `WhisperBackend.transcribe` (Task 3).
- Produces: `POST /voice/transcribe` → `TranscribeOut`, consumed by Task 7's frontend client.

- [ ] **Step 1: Add `TranscribeOut` schema**

In `api/schemas.py`, after `VoiceRequest`:

```python
class TranscribeOut(BaseModel):
    transcript: str
    confidence: float = 0.0
    language: Optional[str] = None
```

- [ ] **Step 2: Write the failing tests (add to the existing `test_routes_voice.py`)**

Append to `tests/unit/api/test_routes_voice.py`:

```python
from backend.layer9_output.schemas import TranscriptResult


class _OkSTT:
    def transcribe(self, audio_bytes, mime_type="audio/webm"):
        return TranscriptResult(transcript="hello nova", confidence=0.95, language="en", ok=True)


class _FailSTT:
    def transcribe(self, audio_bytes, mime_type="audio/webm"):
        return TranscriptResult(ok=False, error="stt down")


def _client_with_stt(stt_backend):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_state] = lambda: SimpleNamespace(voice_backend=None, stt_backend=stt_backend)
    return TestClient(app, raise_server_exceptions=False)


def test_transcribe_returns_text():
    r = _client_with_stt(_OkSTT()).post(
        "/voice/transcribe", files={"file": ("clip.webm", b"FAKEAUDIO", "audio/webm")})
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"] == "hello nova"
    assert body["language"] == "en"


def test_transcribe_503_when_backend_absent():
    r = _client_with_stt(None).post(
        "/voice/transcribe", files={"file": ("clip.webm", b"FAKEAUDIO", "audio/webm")})
    assert r.status_code == 503


def test_transcribe_503_when_transcription_fails():
    r = _client_with_stt(_FailSTT()).post(
        "/voice/transcribe", files={"file": ("clip.webm", b"FAKEAUDIO", "audio/webm")})
    assert r.status_code == 503
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv/bin/pytest tests/unit/api/test_routes_voice.py -v`
Expected: the three new tests FAIL (404, since the route doesn't exist yet); pre-existing tests
still pass.

- [ ] **Step 4: Add the route to `api/routes/voice.py`**

Add these imports at the top (alongside the existing `fastapi` imports):

```python
from fastapi import File, UploadFile
```

Add `TranscribeOut` to the existing `from api.schemas import VoiceRequest` line, making it
`from api.schemas import TranscribeOut, VoiceRequest`.

Add the new endpoint after `synthesize_voice`:

```python
@router.post("/voice/transcribe", response_model=TranscribeOut)
def transcribe_voice(file: UploadFile = File(...), state=Depends(get_state)):
    backend = getattr(state, "stt_backend", None)
    if backend is None:
        raise HTTPException(status_code=503, detail="speech-to-text unavailable")

    audio_bytes = file.file.read()
    result = backend.transcribe(audio_bytes, file.content_type or "audio/webm")
    if not getattr(result, "ok", False):
        logger.warning("transcription failed: %s", getattr(result, "error", "unknown"))
        raise HTTPException(status_code=503, detail="transcription failed")
    return TranscribeOut(transcript=result.transcript, confidence=result.confidence,
                         language=result.language)
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/bin/pytest tests/unit/api/test_routes_voice.py -v`
Expected: all passed (original + 3 new).

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all passed, no regressions.

- [ ] **Step 7: Commit**

```bash
git add api/schemas.py api/routes/voice.py tests/unit/api/test_routes_voice.py
git commit -m "Add POST /voice/transcribe route"
```

---

### Task 7: `docs/API_REFERENCE.md` entry

**Files:**
- Modify: `docs/API_REFERENCE.md`

- [ ] **Step 1: Document the route**

Find the `### \`POST /voice\`` entry and add immediately after it:

```markdown
### `POST /voice/transcribe` → `TranscribeOut`
Multipart audio upload (`file`), transcribed by the local faster-whisper STT backend (fully
offline). Returns `{transcript, confidence, language}`. `503` if the STT backend is unavailable or
transcription fails — the client should fall back to letting the user type.
```

Update the summary route table's `/voice` row to include `/voice/transcribe`, and increment the
total route count by 1.

- [ ] **Step 2: Commit**

```bash
git add docs/API_REFERENCE.md
git commit -m "Document POST /voice/transcribe in API_REFERENCE.md"
```

---

### Task 8: Frontend types + client

**Files:**
- Modify: `frontend/lib/api/types.ts` (append after any existing voice-related types, or at end)
- Modify: `frontend/lib/api/client.ts`

**Interfaces:**
- Produces: `TranscribeOut` type, `transcribeVoice(blob: Blob): Promise<TranscribeOut>` — consumed
  by Task 9.

- [ ] **Step 1: Add the type**

In `frontend/lib/api/types.ts`, append:

```ts
/** POST /voice/transcribe — a dictated utterance transcribed locally. */
export type TranscribeOut = {
  transcript: string;
  confidence: number;
  language: string | null;
};
```

- [ ] **Step 2: Add the client function**

In `frontend/lib/api/client.ts`, add `TranscribeOut` to the `import { ... } from "./types"` block,
then add a new function (near `postVoice`, since it's the multipart sibling of the JSON-body voice
call):

```ts
/** Upload a recorded utterance for transcription. Throws (any non-200, incl. 503) so the caller
 * can fall back to letting the user type instead. */
export async function transcribeVoice(blob: Blob): Promise<TranscribeOut> {
  const form = new FormData();
  form.append("file", blob, "clip.webm");
  const res = await fetch(`${BASE}/voice/transcribe`, { method: "POST", body: form });
  if (!res.ok) throw new ApiError(res.status, `transcription unavailable (${res.status})`);
  return (await res.json()) as TranscribeOut;
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/client.ts
git commit -m "Add TranscribeOut type and transcribeVoice client function"
```

---

### Task 9: `useDictation` hook

**Files:**
- Create: `frontend/lib/hooks/useDictation.ts`
- Create: `frontend/lib/hooks/__tests__/useDictation.test.ts`

**Interfaces:**
- Consumes: `transcribeVoice` (Task 8).
- Produces: `useDictation()` returning `{ supported: boolean, recording: boolean, transcribing:
  boolean, error: string | null, start: () => void, stop: () => void }` — consumed by Task 10.

- [ ] **Step 1: Write the hook**

```ts
"use client";

import { useCallback, useRef, useState } from "react";
import { transcribeVoice } from "@/lib/api/client";

/** Push-to-talk dictation: hold to record, release to transcribe. Progressive enhancement —
 * `supported` is false (and start/stop are no-ops) when the browser lacks MediaRecorder or the
 * user denies mic permission, so callers can hide the control entirely rather than show a broken
 * one. */
export function useDictation(onTranscript: (text: string) => void) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const supported =
    typeof window !== "undefined" &&
    "mediaDevices" in navigator &&
    typeof MediaRecorder !== "undefined";

  const start = useCallback(async () => {
    if (!supported || recording) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setTranscribing(true);
        try {
          const result = await transcribeVoice(blob);
          if (result.transcript) onTranscript(result.transcript);
        } catch {
          setError("Couldn't transcribe that.");
        } finally {
          setTranscribing(false);
        }
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Microphone unavailable.");
    }
  }, [supported, recording, onTranscript]);

  const stop = useCallback(() => {
    if (!recording) return;
    recorderRef.current?.stop();
    setRecording(false);
  }, [recording]);

  return { supported, recording, transcribing, error, start, stop };
}
```

- [ ] **Step 2: Write a unit test for the pure branching logic**

`MediaRecorder`/`getUserMedia` aren't available in the jsdom test environment, so this test covers
the one pure, environment-independent behavior: `supported` is `false` when `MediaRecorder` is
undefined (the jsdom default), and `start()` is then a safe no-op that never throws.

```ts
import { describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDictation } from "@/lib/hooks/useDictation";

describe("useDictation", () => {
  it("reports unsupported and no-ops start() when MediaRecorder is unavailable", async () => {
    const onTranscript = vi.fn();
    const { result } = renderHook(() => useDictation(onTranscript));
    expect(result.current.supported).toBe(false);
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.recording).toBe(false);
    expect(onTranscript).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 3: Run the test**

Run: `cd frontend && ./node_modules/.bin/vitest run lib/hooks/__tests__/useDictation.test.ts`
Expected: 1 passed.

- [ ] **Step 4: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/hooks/useDictation.ts frontend/lib/hooks/__tests__/useDictation.test.ts
git commit -m "Add useDictation push-to-talk hook"
```

---

### Task 10: Mic button in `Composer.tsx`

**Files:**
- Modify: `frontend/components/chat/Composer.tsx`

**Interfaces:**
- Consumes: `useDictation` (Task 9).

- [ ] **Step 1: Add the mic button**

Add imports at the top:

```tsx
import { Mic } from "lucide-react";
import { useDictation } from "@/lib/hooks/useDictation";
```

Inside the `Composer` function body, after the `canSend` line, add:

```tsx
  const dictation = useDictation((text) => onChange(value ? `${value} ${text}` : text));
```

Add the mic button in the JSX, between the `<textarea>` and the send `<button>`:

```tsx
      {dictation.supported && (
        <button
          type="button"
          disabled={disabled}
          onMouseDown={dictation.start}
          onMouseUp={dictation.stop}
          onMouseLeave={dictation.stop}
          onTouchStart={dictation.start}
          onTouchEnd={dictation.stop}
          aria-label="Hold to talk"
          className={cn(
            "mb-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition-colors",
            dictation.recording
              ? "border-brass/40 bg-brass/10 text-brass"
              : "border-hairline/50 text-ink-faint hover:text-ink-soft"
          )}
        >
          <Mic size={15} className={dictation.transcribing ? "animate-pulse" : ""} />
        </button>
      )}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 3: Lint**

Run: `cd frontend && ./node_modules/.bin/eslint components/chat/Composer.tsx`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/chat/Composer.tsx
git commit -m "Add push-to-talk mic button to Composer"
```

---

### Task 11: Live verification

**Files:** None (verification only).

- [ ] **Step 1: Run the full backend suite**

Run: `.venv/bin/pytest -q`
Expected: all passed.

- [ ] **Step 2: Run frontend lint + typecheck + unit tests**

Run: `cd frontend && ./node_modules/.bin/eslint . && ./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/vitest run`
Expected: all clean, all passed.

- [ ] **Step 3: Build and run the real `stt` service, restart the API against it**

```bash
docker compose -f docker/docker-compose.yml up -d --build stt
```

Restart the local API (see `scripts/run_local.sh`) so `build_stt_backend` picks up the running
service, with `STT_URL` pointed at the loopback port from Task 2 (`http://127.0.0.1:8881`).

- [ ] **Step 4: Real round trip via curl**

```bash
curl -s -X POST http://127.0.0.1:8000/voice/transcribe \
  -F "file=@/tmp/test.wav;type=audio/wav" | python3 -m json.tool
```

Confirm a 200 with a real (even if inaccurate-on-a-tone) `transcript` field — this is the proof that
`WhisperBackend`'s field mapping from Task 3 actually matches the live service's real response, not
just the mocked test.

- [ ] **Step 5: Real round trip via the browser**

Start the frontend dev server, open `/chat`, hold the mic button, speak a short sentence, release,
confirm the transcript appears in the composer editable and correct (or close — small local models
aren't perfect, but it should be recognizably right).

- [ ] **Step 6: Update `frontend/DEFERRED_WORK.md`**

Update item #5's "Speech-to-text (voice input)" bullet: change it from "needs an STT
model/endpoint" to a `[done, 2026-08-10]` note pointing at this feature, keeping the existing
WebSocket-reasoning text (added in the design-spec commit) intact since that part is still accurate.

- [ ] **Step 7: Commit**

```bash
git add frontend/DEFERRED_WORK.md
git commit -m "Mark speech-to-text deferred-work item done"
```
