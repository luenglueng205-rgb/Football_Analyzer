import os
import asyncio
from langchain_openai import ChatOpenAI
from browser_use import Agent

class VisualBrowser:
    """
    P3 阶段视觉交互引擎：完全基于自然语言指令驱动浏览器，抛弃一切 HTML 解析代码。
    """
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        
        # browser-use 强依赖 LangChain 接口
        self.llm = ChatOpenAI(
            model="gpt-4o", # 必须使用支持视觉的多模态大模型
            api_key=api_key,
            base_url=base_url,
            max_tokens=2048
        )

    async def extract_info(self, task_instruction: str) -> str:
        """
        向浏览器下达自然语言抓取指令，返回 AI 总结的纯文本结果。
        """
        try:
            agent = Agent(
                task=task_instruction,
                llm=self.llm
            )
            print(f"    [👀 VisualBrowser] 正在拉起视觉智能体执行任务...")
            # 运行 Agent，返回执行历史
            history = await agent.run()
            # 提取最后一步的最终结果
            if history and hasattr(history, 'final_result'):
                 return history.final_result()
            return str(history)
        except Exception as e:
            print(f"    [👀 VisualBrowser] 视觉交互失败: {e}")
            return f"Error: {e}"
