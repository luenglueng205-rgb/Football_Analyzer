import os


def test_llm_config_deepseek_fallback_for_chat():
    os.environ["AFA_SKIP_DOTENV"] = "1"
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OPENAI_API_BASE", None)
    os.environ.pop("OPENAI_BASE_URL", None)
    os.environ.pop("OPENAI_MODEL", None)
    os.environ.pop("MODEL_NAME", None)

    os.environ["DEEPSEEK_API_KEY"] = "deepseek-key"
    os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com"

    from tools.llm_config import get_llm_settings

    cfg = get_llm_settings(purpose="chat")
    assert cfg["api_key"] == "deepseek-key"
    assert cfg["base_url"].endswith("/v1")
    assert "deepseek" in cfg["model"]


def test_llm_config_prefers_openai_when_present():
    os.environ["AFA_SKIP_DOTENV"] = "1"
    os.environ["OPENAI_API_KEY"] = "openai-key"
    os.environ["OPENAI_API_BASE"] = "https://api.openai.com/v1"
    os.environ["OPENAI_MODEL"] = "gpt-4o-mini"

    os.environ["DEEPSEEK_API_KEY"] = "deepseek-key"
    os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com/v1"

    from tools.llm_config import get_llm_settings

    cfg = get_llm_settings(purpose="chat")
    assert cfg["api_key"] == "openai-key"
    assert cfg["base_url"] == "https://api.openai.com/v1"
    assert cfg["model"] == "gpt-4o-mini"
