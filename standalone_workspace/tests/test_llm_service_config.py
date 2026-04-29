import os


def test_llm_service_client_uses_deepseek_when_only_deepseek_key_present():
    os.environ["AFA_SKIP_DOTENV"] = "1"
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OPENAI_API_BASE", None)
    os.environ.pop("OPENAI_BASE_URL", None)
    os.environ.pop("OPENAI_MODEL", None)
    os.environ.pop("MODEL_NAME", None)

    os.environ["DEEPSEEK_API_KEY"] = "deepseek-key"
    os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com"

    from tools.llm_service import LLMService

    client = LLMService.get_client()
    assert "api.deepseek.com/v1" in str(getattr(client, "base_url", ""))
