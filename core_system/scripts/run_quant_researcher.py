import os
import sys
import asyncio
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from core_system.agents.ai_quant_researcher import QuantResearcherAgent

async def main():
    load_dotenv()
    
    print("==================================================")
    print("🧠 [AI Quant Researcher] 全自动量化投研沙箱启动")
    print("==================================================")
    print("-> 警告：此 Agent 将自主编写 Python 策略代码，并在沙箱中执行回测。")
    print("-> 安全策略：Human Approval Gate (人工审批门) 已强制开启。\n")
    
    # 确保 API Key 存在
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ 错误: 未配置大模型 API Key。请在 .env 中设置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY。")
        return
        
    try:
        # 初始化研究员，强制开启人工审批
        researcher = QuantResearcherAgent(require_human_approval=True)
        
        # 运行 2 轮迭代寻找高夏普比率策略 (演示用 2 轮，生产可设为 10)
        print("-> 开始自我迭代寻优 (Max Iterations: 2)...\n")
        await researcher.auto_research_loop(max_iterations=2)
        
    except Exception as e:
        print(f"\n❌ 投研循环异常中断: {e}")

if __name__ == "__main__":
    asyncio.run(main())