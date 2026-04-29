import os


def test_state_graph_uses_deepseek_base_url_when_only_deepseek_key_present():
    os.environ["AFA_SKIP_DOTENV"] = "1"
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OPENAI_BASE_URL", None)
    os.environ.pop("OPENAI_API_BASE", None)
    os.environ.pop("MODEL_NAME", None)

    os.environ["DEEPSEEK_API_KEY"] = "deepseek-key"
    os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com"
    os.environ["DEEPSEEK_CHAT_MODEL"] = "deepseek-chat"

    from core.agentic_os.llm_factory import get_base_llm_kwargs

    kwargs = get_base_llm_kwargs()
    assert kwargs["api_key"] == "deepseek-key"
    assert kwargs["base_url"] == "https://api.deepseek.com/v1"
    assert "deepseek" in kwargs["model"]
