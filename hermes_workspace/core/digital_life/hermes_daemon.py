import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HermesDaemon")

def start_hermes_loop():
    """
    Hermes Agent 深度适配版 Daemon。
    专为 Hermes-2-Pro / Hermes-3 设计，采用极其严格的 System Prompt，
    要求模型 100% 使用 Function Calling 输出结构化分析结果。
    """
    logger.info("🧠 [Hermes Version] 独立函数调用循环已启动...")
    logger.info("-> 采用严格 JSON Schema 约束，去除所有无用对话，专注量化风控。")
    
    system_prompt = '''
You are an expert quantitative sports analyst.
You must ONLY respond with valid JSON matching the provided tool schemas.
Do not include any conversational filler.
    '''
    logger.info(f"已加载 Hermes 专属 System Prompt:\n{system_prompt}")
    logger.info("-> (此为入口占位程序，生产环境请将 hermes_adapter.py 挂载至您的 Hermes API 客户端)")

if __name__ == "__main__":
    start_hermes_loop()
