"""Fixtures for docker-backed infra tests. Every fixture probes its service and skips if it's down,
so `pytest tests/` stays green with no stack running."""
import os
import socket

import pytest


def _reachable(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def ollama_url():
    url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    host = url.split("//", 1)[-1].split(":")[0]
    port = int(url.rsplit(":", 1)[-1])
    if not _reachable(host, port):
        pytest.skip(f"ollama not reachable at {url}")
    return url


@pytest.fixture
def chroma_hostport():
    host = os.environ.get("CHROMA_HOST", "localhost")
    port = int(os.environ.get("CHROMA_PORT", "8001"))
    if not _reachable(host, port):
        pytest.skip(f"chroma not reachable at {host}:{port}")
    return host, port


@pytest.fixture
def postgres_url():
    url = os.environ.get("DATABASE_URL", "postgresql+psycopg://nova:nova@localhost:5432/nova")
    hostport = url.rsplit("@", 1)[-1].split("/", 1)[0]
    host, _, port = hostport.partition(":")
    if not _reachable(host, int(port or 5432)):
        pytest.skip(f"postgres not reachable at {hostport}")
    return url
