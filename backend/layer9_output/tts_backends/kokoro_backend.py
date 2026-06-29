"""Kokoro TTS backend (architecture doc §5.7).

Integrates with the Kokoro TTS service (Docker, ``localhost:8880``) via its OpenAI-compatible
``/v1/audio/speech`` endpoint. The HTTP transport is injected (``request_fn``) so the backend
is fully testable offline and degrades gracefully — any transport error yields a non-ok
``AudioResult`` rather than raising, so SC-3 can fall back to text.
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer9_output.schemas import AudioResult
from backend.layer9_output.tts_backends.base_backend import TTSBackend

_DEFAULT_VOICES = ["af_sky", "af_bella", "af_nicole", "am_adam", "bf_emma"]


class KokoroBackend(TTSBackend):
    def __init__(
        self,
        endpoint: str = "http://localhost:8880",
        default_voice: str = "af_sky",
        model: str = "kokoro",
        default_rate: float = 1.0,
        request_fn: Optional[Callable] = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.default_voice = default_voice
        self.model = model
        self.default_rate = default_rate
        self._request_fn = request_fn

    def synthesize(
        self, ssml_text: str, voice_id: Optional[str] = None,
        speech_rate: Optional[float] = None,
    ) -> AudioResult:
        if self._request_fn is None:
            return AudioResult(ok=False, error="no TTS transport configured")
        payload = {
            "model": self.model,
            "input": ssml_text,
            "voice": voice_id or self.default_voice,
            "speed": speech_rate if speech_rate is not None else self.default_rate,
            "response_format": "mp3",
        }
        try:
            resp = self._request_fn("POST", f"{self.endpoint}/v1/audio/speech", payload)
        except Exception as exc:  # transport/connection error → graceful fallback
            return AudioResult(ok=False, error=f"kokoro request failed: {exc}")
        if not getattr(resp, "ok", False):
            return AudioResult(ok=False, error=f"kokoro status {getattr(resp, 'status_code', '?')}")
        return AudioResult(audio_bytes=resp.content, content_type="audio/mpeg", ok=True)

    def supports_ssml(self) -> bool:
        return True

    def get_available_voices(self) -> list:
        return list(_DEFAULT_VOICES)

    def health_check(self) -> bool:
        if self._request_fn is None:
            return False
        try:
            resp = self._request_fn("GET", f"{self.endpoint}/health")
        except Exception:
            return False
        return bool(getattr(resp, "ok", False))
