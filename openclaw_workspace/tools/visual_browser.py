import os

_agent_cls = None
_chat_openai_cls = None


def _load_browser_agent():
    global _agent_cls
    if _agent_cls is None:
        from browser_use import Agent as BrowserUseAgent

        _agent_cls = BrowserUseAgent
    return _agent_cls


def _load_chat_openai():
    global _chat_openai_cls
    if _chat_openai_cls is None:
        from langchain_openai import ChatOpenAI

        _chat_openai_cls = ChatOpenAI
    return _chat_openai_cls


class VisualBrowser:
    """
    P3 阶段视觉交互引擎：完全基于自然语言指令驱动浏览器，抛弃一切 HTML 解析代码。
    """
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        chat_openai_cls = _load_chat_openai()
        
        # browser-use 强依赖 LangChain 接口
        self.llm = chat_openai_cls(
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
            agent_cls = _load_browser_agent()
            agent = agent_cls(
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
