"""Voice route — Layer-9 SSML synthesis dispatched to a TTS backend."""
import pytest
pytest.importorskip("fastapi")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_state
from api.routes.voice import router
from backend.layer9_output.schemas import AudioResult, TranscriptResult


class _OkBackend:
    def synthesize(self, ssml_text, voice_id=None, speech_rate=None):
        self.seen_ssml = ssml_text
        return AudioResult(audio_bytes=b"ID3-fake-mp3", content_type="audio/mpeg", ok=True)


class _FailBackend:
    def synthesize(self, ssml_text, voice_id=None, speech_rate=None):
        return AudioResult(ok=False, error="kokoro down")


def _client(backend):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_state] = lambda: SimpleNamespace(voice_backend=backend)
    return TestClient(app, raise_server_exceptions=False)


def test_voice_returns_audio_bytes():
    r = _client(_OkBackend()).post("/voice", json={"text": "Hello there.", "conversation_mode": "casual"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"ID3-fake-mp3"


def test_voice_503_when_backend_absent():
    assert _client(None).post("/voice", json={"text": "hi"}).status_code == 503


def test_voice_503_when_synthesis_fails():
    assert _client(_FailBackend()).post("/voice", json={"text": "hi"}).status_code == 503


def test_voice_rejects_empty_text():
    assert _client(_OkBackend()).post("/voice", json={"text": "  "}).status_code == 422


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
