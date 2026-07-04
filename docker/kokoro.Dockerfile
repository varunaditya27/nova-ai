# Kokoro TTS image — OpenAI-compatible speech API on :8880 (used by Layer 9 voice synthesis).
# Wraps the upstream FastAPI build so the image is pinned and buildable from this repo.
FROM ghcr.io/remsky/kokoro-fastapi-cpu:latest

EXPOSE 8880
