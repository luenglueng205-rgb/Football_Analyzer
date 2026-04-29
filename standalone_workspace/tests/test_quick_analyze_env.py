import os


def test_quick_analyze_uses_deepseek_base_url_when_only_deepseek_key_present():
    os.environ["AFA_SKIP_DOTENV"] = "1"
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OPENAI_API_BASE", None)
    os.environ.pop("OPENAI_BASE_URL", None)
    os.environ.pop("OPENAI_MODEL", None)
    os.environ.pop("MODEL_NAME", None)

    os.environ["DEEPSEEK_API_KEY"] = "deepseek-key"
    os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com"

    from scripts import quick_analyze

    cfg = quick_analyze.get_client_settings()
    assert cfg["api_key"] == "deepseek-key"
    assert cfg["base_url"] == "https://api.deepseek.com/v1"

