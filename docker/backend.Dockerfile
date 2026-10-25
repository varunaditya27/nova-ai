# syntax=docker/dockerfile:1
# Nova AI backend — FastAPI app image.
# Build from the repo root as context:  docker build -f docker/backend.Dockerfile -t nova-ai:latest .
# (docker-compose sets context: .. so paths below are repo-root relative.)
FROM python:3.11-slim

# Run as an unprivileged user (container-hardening).
RUN useradd --create-home --uid 10001 nova

WORKDIR /app

# setuptools needs the package directories to build, so the source is copied before install.
# The pip cache mount keeps downloaded wheels across builds, so a source-only change does not re-download dependencies.
COPY --chown=nova:nova . .
RUN --mount=type=cache,target=/root/.cache/pip pip install ".[infra,api]"

USER nova

EXPOSE 8000
# The api/ layer is a later increment; this CMD activates once api.main:app exists
# (compose only starts this service under the `app` profile).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
