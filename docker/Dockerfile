# Nova AI backend — FastAPI app image.
# Build from the repo root as context:  docker build -f docker/Dockerfile -t nova-ai:latest .
# (docker-compose sets context: .. so paths below are repo-root relative.)
FROM python:3.11-slim

# Run as an unprivileged user (container-hardening).
RUN useradd --create-home --uid 10001 nova

WORKDIR /app

# Install deps first for layer caching; only the infra extra is needed at runtime.
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[infra,api]"

# Copy source and hand ownership to the unprivileged user.
COPY . .
RUN chown -R nova:nova /app

USER nova

EXPOSE 8000
# The api/ layer is a later increment; this CMD activates once api.main:app exists
# (compose only starts this service under the `app` profile).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
