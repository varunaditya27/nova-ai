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
