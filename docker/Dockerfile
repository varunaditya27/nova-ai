# Backend Dockerfile
#
# Purpose: Containerize Nova AI backend for production deployment
#
# Build stages:
#   1. Base: Python 3.11 slim image
#   2. Dependencies: Install system + Python packages
#   3. Code: Copy source, set working directory
#   4. Configuration: Set environment variables, ports
#
# Runtime:
#   - Entry point: uvicorn server on 0.0.0.0:8000
#   - Volumes: Mount config/, data/, nova-data/ for persistence
#   - Environment: Load from .env or docker-compose
#
# Health check:
#   - GET /health endpoint for Kubernetes/Docker readiness
#
# Development:
#   - Use docker-compose up for local testing
#   - Volumes mount source for live code reload (if configured)
