import textwrap

from config import load_config


def test_load_defaults_returns_role_based_llm_config():
    cfg = load_config(env={"GROQ_API_KEY": "sk-test"})
    assert cfg["llm"]["system1"]["provider"] == "ollama"
    assert cfg["llm"]["system2"]["provider"] == "groq"
    assert cfg["llm"]["embeddings"]["model"] == "nomic-embed-text"


def test_env_interpolation_resolves_secret():
    cfg = load_config(env={"GROQ_API_KEY": "sk-live-123"})
    assert cfg["llm"]["providers"]["groq"]["api_key"] == "sk-live-123"


def test_env_default_used_when_var_absent():
    cfg = load_config(env={"GROQ_API_KEY": "x"})  # OLLAMA_BASE_URL absent
    assert cfg["llm"]["providers"]["ollama"]["base_url"] == "http://ollama:11434"


def test_override_file_deep_merges(tmp_path):
    override = tmp_path / "prod.yaml"
    override.write_text(textwrap.dedent("""
        llm:
          system2:
            provider: ollama
    """))
    cfg = load_config(str(override), env={"GROQ_API_KEY": "x"})
    assert cfg["llm"]["system2"]["provider"] == "ollama"
    # untouched sibling keys survive the deep merge
    assert cfg["llm"]["system2"]["model"] == "llama-3.3-70b-versatile"
