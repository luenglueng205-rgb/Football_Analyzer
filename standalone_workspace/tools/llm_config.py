import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


def _normalize_base_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if url.endswith("/"):
        url = url[:-1]
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


def load_project_env(*, override: bool = False) -> None:
    if os.getenv("AFA_SKIP_DOTENV") == "1":
        return
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env", override=override)


def get_llm_settings(*, purpose: str = "chat") -> Dict[str, str]:
    load_project_env()

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    api_key = openai_key or deepseek_key

    base_url = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or os.getenv("OPENAI_BASE")
        or os.getenv("DEEPSEEK_API_BASE")
        or os.getenv("DEEPSEEK_BASE_URL")
        or ""
    )

    base_url = _normalize_base_url(base_url) if base_url else ""

    model = (
        os.getenv("MODEL_NAME")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("OPENAI_VISION_MODEL")
        or ""
    ).strip()

    if not model:
        if deepseek_key and not openai_key:
            model = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat").strip()
        else:
            model = "gpt-4o-mini"

    if purpose == "reasoning":
        api_key = deepseek_key or api_key
        reasoning_base = os.getenv("DEEPSEEK_API_BASE", "").strip() or base_url
        base_url = _normalize_base_url(reasoning_base) if reasoning_base else base_url
        model = os.getenv("DEEPSEEK_REASONING_MODEL", "deepseek-reasoner").strip()

    if purpose == "vision":
        model = os.getenv("OPENAI_VISION_MODEL", model).strip()

    if not base_url:
        base_url = "https://api.openai.com/v1"

    return {"api_key": api_key, "base_url": base_url, "model": model}
