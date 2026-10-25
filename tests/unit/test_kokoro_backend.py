"""Tests for SC-3 Kokoro TTS backend (architecture doc §5.7)."""

from backend.layer9_output.tts_backends.base_backend import TTSBackend
from backend.layer9_output.tts_backends.kokoro_backend import KokoroBackend


class _Resp:
    def __init__(self, ok=True, content=b"AUDIO", status_code=200):
        self.ok, self.content, self.status_code = ok, content, status_code


def _recording_client(resp=None, raises=False):
    calls = []

    def request_fn(method, url, payload=None):
        calls.append({"method": method, "url": url, "payload": payload})
        if raises:
            raise ConnectionError("kokoro unreachable")
        return resp or _Resp()
    return request_fn, calls


def test_kokoro_is_a_tts_backend():
    assert isinstance(KokoroBackend(request_fn=lambda *a, **k: _Resp()), TTSBackend)


def test_synthesize_returns_audio_on_success():
    fn, _ = _recording_client(_Resp(content=b"MP3DATA"))
    res = KokoroBackend(request_fn=fn).synthesize("<speak>hi</speak>")
    assert res.ok is True and res.audio_bytes == b"MP3DATA"


def test_synthesize_sends_openai_compatible_payload():
    fn, calls = _recording_client()
    KokoroBackend(request_fn=fn, default_voice="af_sky").synthesize("hello", voice_id="af_bella")
    payload = calls[-1]["payload"]
    assert payload["input"] == "hello"
    assert payload["voice"] == "af_bella"
    assert "model" in payload
    assert calls[-1]["url"].endswith("/v1/audio/speech")


def test_synthesize_switches_ssml_on():
    fn, calls = _recording_client()
    KokoroBackend(request_fn=fn).synthesize("<speak>hi</speak>")
    payload = calls[-1]["payload"]
    assert payload["ssml"] is True and payload["allow_voice_tags"] is True


def test_connection_error_is_graceful():
    fn, _ = _recording_client(raises=True)
    res = KokoroBackend(request_fn=fn).synthesize("hi")
    assert res.ok is False and res.error


def test_no_client_configured_fails_gracefully():
    res = KokoroBackend(request_fn=None).synthesize("hi")
    assert res.ok is False


def test_health_check_true_when_reachable():
    fn, _ = _recording_client(_Resp(ok=True))
    assert KokoroBackend(request_fn=fn).health_check() is True


def test_health_check_false_when_unreachable():
    fn, _ = _recording_client(raises=True)
    assert KokoroBackend(request_fn=fn).health_check() is False


def test_supports_ssml():
    assert KokoroBackend().supports_ssml() is True


def test_set_voice_changes_default():
    fn, calls = _recording_client()
    k = KokoroBackend(request_fn=fn, default_voice="af_sky")
    k.set_voice("af_nicole")
    k.synthesize("hi")
    assert calls[-1]["payload"]["voice"] == "af_nicole"
