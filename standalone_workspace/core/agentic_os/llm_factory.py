from tools.llm_config import get_llm_settings


def get_base_llm_kwargs():
    cfg = get_llm_settings(purpose="chat")
    return {"api_key": cfg["api_key"], "base_url": cfg["base_url"], "model": cfg["model"], "temperature": 0.7}


def get_tool_llm_kwargs():
    cfg = get_llm_settings(purpose="chat")
    return {"api_key": cfg["api_key"], "base_url": cfg["base_url"], "model": cfg["model"], "temperature": 0.0}

