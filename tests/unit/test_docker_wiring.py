"""The addresses the backend uses inside Docker must match the ports the compose services really serve on."""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]


def _container_port(service: str) -> str:
    compose = yaml.safe_load((ROOT / "docker" / "docker-compose.yml").read_text())
    return compose["services"][service]["ports"][0].rsplit(":", 1)[1]


def _default_port(config_text: str, key: str) -> str:
    return re.search(rf"{key}: \$\{{\w+:-http://\w+:(\d+)\}}", config_text).group(1)


@pytest.mark.parametrize("section,service", [("tts", "kokoro"), ("stt", "stt")])
def test_backend_default_address_uses_the_container_port(section, service):
    config_text = (ROOT / "config" / "defaults.yaml").read_text()
    block = re.search(rf"^{section}:.*?^\s+endpoint: (.+)$", config_text, re.S | re.M).group(0)
    assert _default_port(block, "endpoint") == _container_port(service)
