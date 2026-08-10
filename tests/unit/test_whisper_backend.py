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
