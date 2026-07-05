import os
import socket
import urllib.request

import pytest


def _up(host, port):
    try:
        with socket.create_connection((host, int(port)), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.mark.docker
def test_backend_health_endpoint():
    host, port = os.environ.get("API_HOST", "localhost"), int(os.environ.get("API_PORT", "8000"))
    if not _up(host, port):
        pytest.skip("backend not running")
    with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2) as r:
        assert r.status == 200
