"""Configuration loader.

`load_config()` reads `defaults.yaml` then deep-merges each named override file over it and resolves
`${VAR}` / `${VAR:-default}` placeholders from the environment. Nested dicts merge key-wise; scalars
and lists replace. Secrets and hostnames come from env — never hardcode them in YAML.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent
_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _interpolate(value: Any, env: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: _interpolate(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v, env) for v in value]
    if isinstance(value, str):
        def repl(match: re.Match) -> str:
            token = match.group(1)
            name, _, default = token.partition(":-")
            return env.get(name, default)
        return _PLACEHOLDER.sub(repl, value)
    return value


def _resolve(name: str) -> Path:
    p = Path(name)
    return p if p.is_absolute() else _CONFIG_DIR / p


def load_config(*names: str, env: Mapping[str, str] | None = None) -> dict:
    env = os.environ if env is None else env
    defaults_path = _CONFIG_DIR / "defaults.yaml"
    if not defaults_path.exists():
        raise FileNotFoundError(defaults_path)
    merged: dict = yaml.safe_load(defaults_path.read_text()) or {}
    for name in names:
        path = _resolve(name)
        if not path.exists():
            continue
        merged = _deep_merge(merged, yaml.safe_load(path.read_text()) or {})
    return _interpolate(merged, env)
