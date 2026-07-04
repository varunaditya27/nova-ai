"""Cross-layer consistency guard — mechanical checks that prevent integration drift.

These tests assert structural invariants of the whole system rather than any single layer's
behaviour: every layer package imports and exposes its documented entry point, every per-layer
config parses, the pipeline wires the layers, and the filesystem matches the 13-layer map. If a
future change breaks a cross-layer contract (renamed export, deleted module, dropped config),
exactly one of these fails with a clear message.
"""

import glob
import importlib

import pytest
import yaml

# (module path, primary public entry symbol) for each of the 13 layers.
LAYER_ENTRYPOINTS = [
    ("backend.layer1_input", "process_input_event"),
    ("backend.layer2_memory", "memory_arbiter"),
    ("backend.layer3_reasoning", "build_emotion_intent_packet"),
    ("backend.layer4_persona", "generate_semantic_draft"),
    ("backend.layer5_relationship", "build_social_intelligence_packet"),
    ("backend.layer6_proactivity", "run_proactive_cycle"),
    ("backend.layer7_goals", "run_goal_pipeline"),
    ("backend.layer8_tools", "ToolManager"),
    ("backend.layer9_output", "deliver"),
    ("backend.layer10_longitudinal", "assemble_context_packet"),
    ("backend.layer11_safety", "SafetyAgent"),
    ("backend.layer12_privacy", "PrivacyAgent"),
    ("backend.layer13_onboarding", "ColdStartEngine"),
]


@pytest.mark.parametrize("module_path,_symbol", LAYER_ENTRYPOINTS)
def test_every_layer_package_imports(module_path, _symbol):
    assert importlib.import_module(module_path) is not None


@pytest.mark.parametrize("module_path,symbol", LAYER_ENTRYPOINTS)
def test_every_layer_exposes_its_entrypoint(module_path, symbol):
    mod = importlib.import_module(module_path)
    assert hasattr(mod, symbol), f"{module_path} is missing its entry point '{symbol}'"


def test_all_thirteen_layers_present_on_disk():
    dirs = sorted(glob.glob("backend/layer*_*/__init__.py"))
    assert len(dirs) == 13


@pytest.mark.parametrize("n", range(1, 14))
def test_every_layer_config_parses_and_is_namespaced(n):
    with open(f"config/layer{n}.yaml") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict)
    assert f"layer{n}" in data, f"config/layer{n}.yaml must be namespaced under 'layer{n}:'"


def test_pipeline_and_api_import():
    # `backend.pipeline` and the `api` package are pure-stdlib importable; `api.main` is the FastAPI
    # app and requires the `api` extra, so it only imports where fastapi is installed.
    for m in ("backend.pipeline", "api"):
        assert importlib.import_module(m) is not None
    pytest.importorskip("fastapi")
    assert importlib.import_module("api.main") is not None


def test_orchestrator_threads_all_steps():
    # The PipelineSteps contract must expose one hook per orchestrated layer concern.
    from backend.pipeline import PipelineSteps
    expected = {"perceive", "recall", "cold_start", "classify", "safety_scan", "build_persona",
                "plan", "refine", "guardrails", "escalate", "deliver", "state_update"}
    assert expected <= set(PipelineSteps.__dataclass_fields__)
