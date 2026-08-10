from config import load_config


def test_api_and_default_user_config_present():
    cfg = load_config(env={})
    assert cfg["system"]["default_user_id"] == "local-user"
    assert cfg["api"]["port"] == 8000
    assert cfg["api"]["cors_origins"] == ["http://localhost:3000"]
