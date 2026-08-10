# faster-whisper STT server — OpenAI-Whisper-API-compatible transcription on :8000 (used by
# Layer 9 speech-to-text). Wraps the upstream image so it's pinned and buildable from this repo,
# matching kokoro.Dockerfile's pattern exactly.
FROM fedirz/faster-whisper-server:latest-cpu

ENV WHISPER__MODEL=Systran/faster-whisper-small

EXPOSE 8000
