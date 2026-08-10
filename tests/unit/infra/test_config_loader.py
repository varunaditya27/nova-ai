import textwrap

from config import load_config


def test_load_defaults_returns_role_based_llm_config():
    cfg = load_config(env={})
    assert cfg["llm"]["system1"]["provider"] == "ollama"
    assert cfg["llm"]["system2"]["provider"] == "ollama"
    assert cfg["llm"]["embeddings"]["model"] == "nomic-embed-text"


def test_env_interpolation_resolves_model_tier_override():
    cfg = load_config(env={"NOVA_MAIN_MODEL": "qwen2.5:14b"})
    assert cfg["llm"]["system1"]["model"] == "qwen2.5:14b"
    assert cfg["llm"]["system2"]["model"] == "qwen2.5:14b"


def test_env_default_used_when_var_absent():
    cfg = load_config(env={})
    assert cfg["llm"]["providers"]["ollama"]["base_url"] == "http://ollama:11434"
    assert cfg["llm"]["system1"]["model"] == "qwen2.5:7b"
    assert cfg["llm"]["intent"]["model"] == "gemma2:2b"


def test_override_file_deep_merges(tmp_path):
    override = tmp_path / "prod.yaml"
    override.write_text(textwrap.dedent("""
        llm:
          system2:
            temperature: 0.9
    """))
    cfg = load_config(str(override), env={})
    assert cfg["llm"]["system2"]["temperature"] == 0.9
    # untouched sibling keys survive the deep merge
    assert cfg["llm"]["system2"]["provider"] == "ollama"
