import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
import httpx

# 加载 .env
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
            api_key = os.getenv("OPENAI_API_KEY", "dummy_key")
            base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
            
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
    def generate_report(cls, system_prompt: str, data_context: str) -> str:
        """
        根据 Agent 提供的上下文数据，生成自然语言分析报告
        """
        try:
            client = cls.get_client()
            # 如果没有配置真实的API KEY，返回模拟数据（避免程序报错中断）
            if client.api_key == "dummy_key" or client.api_key == "your_api_key_here":
                raise ValueError("请在环境变量中配置有效的 OPENAI_API_KEY 以启动真实的 AI 推理。")

            response = client.chat.completions.create(
                model="gpt-4o-mini", # 或 deepseek-chat, gpt-3.5-turbo
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

