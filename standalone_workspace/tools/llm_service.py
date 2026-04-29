import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI
from typing import Dict, Any
import httpx

# 加载 .env
if os.getenv("AFA_SKIP_DOTENV") != "1":
    load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    """
    统一的 LLM 调用服务
    """
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            from tools.llm_config import get_llm_settings

            cfg = get_llm_settings(purpose="chat")
            api_key = cfg["api_key"] or "dummy_key"
            base_url = cfg["base_url"]
            
            # 兼容处理：防止旧版本 openai 报错
            try:
                cls._client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    http_client=httpx.Client()
                )
            except Exception as e:
                # 兼容极简模式
                cls._client = OpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
        return cls._client

    @classmethod
    async def generate_report_async(cls, system_prompt: str, data_context: str, role: str = "Analyst", task_type: str = "general") -> str:
        """
        基于任务类型路由到最佳模型 (Model Router)
        task_type: 'general', 'vision', 'reasoning', 'summarization'
        """
        import os
        from openai import AsyncOpenAI
        import json
        
        from tools.llm_config import get_llm_settings

        purpose = "chat"
        if task_type == "vision":
            purpose = "vision"
        elif task_type == "reasoning":
            purpose = "reasoning"

        cfg = get_llm_settings(purpose=purpose)
        api_key = cfg["api_key"] or "dummy_key"
        base_url = cfg["base_url"]
        model = cfg["model"]
            
        if api_key == "dummy_key" or api_key == "your_api_key_here":
            if role == "AAR Analyst":
                return json.dumps({"success": False, "reflection": "Mock reflection.", "lesson": "Mock lesson."})
            raise ValueError(f"请在环境变量中配置有效的 API_KEY ({task_type} 需要) 以启动真实的 AI 推理。")
            
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data_context}
            ],
            temperature=0.3,
            max_tokens=800
        )
        return response.choices[0].message.content

    @classmethod
    def generate_report(cls, system_prompt: str, data_context: str, role: str = "Analyst") -> str:
        """
        根据 Agent 提供的上下文数据，生成自然语言分析报告
        """
        try:
            from tools.llm_config import get_llm_settings

            client = cls.get_client()
            # 如果没有配置真实的API KEY，返回模拟数据（避免程序报错中断）
            if client.api_key == "dummy_key" or client.api_key == "your_api_key_here":
                raise ValueError("请在环境变量中配置有效的 OPENAI_API_KEY 以启动真实的 AI 推理。")

            cfg = get_llm_settings(purpose="chat")
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请根据以下硬核数据，生成专业的足彩分析研报：\n{data_context}"}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"❌ AI 分析报告生成失败，请检查网络或 API Key。错误信息：{e}"
