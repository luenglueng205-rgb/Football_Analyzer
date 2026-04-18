"""
OpenClaw Main Agent (Native Multi-Agent OS)
这是在 OpenClaw 中最高权限的主代理入口。当用户向 `main` 代理发起请求时，该脚本将被调用。
它将基于 OpenClaw 的生态系统，把任务转交给 `orchestrator`（调度中心）进行处理。
"""

import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = WORKSPACE_ROOT / "runtime" / "football_analyzer"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))
SRC_DIR = WORKSPACE_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Import specific SubAgents from the native runtime
from agents.orchestrator import OrchestratorAgent
from agents.scout import ScoutAgent
from agents.analyst import AnalystAgent
from agents.strategist import StrategistAgent
from agents.risk_manager import RiskManagerAgent
from tools.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OpenClawMainAgent")

class OpenClawMainAgent:
    """
    The Main Orchestrator Gateway for OpenClaw.
    """
    def __init__(self, online: bool = False):
        self.online = online
        self.orchestrator = OrchestratorAgent()
        
        # Register subagents to the orchestrator's bus
        self.orchestrator.register_agent("scout", ScoutAgent())
        self.orchestrator.register_agent("analyst", AnalystAgent())
        self.orchestrator.register_agent("strategist", StrategistAgent())
        self.orchestrator.register_agent("risk_manager", RiskManagerAgent())
        
        self.memory = MemoryManager()

    async def analyze_and_trade(self, lottery_type: str, date_str: str) -> Dict[str, Any]:
        """
        触发完整的分析循环
        """
        logger.info(f"Starting analysis for {lottery_type} on {date_str} via Multi-Agent System")
        
        try:
            # 模拟用户任务，直接分发给 orchestrator
            task = {
                "type": "full_analysis",
                "params": {
                    "lottery_type": lottery_type.lower(),
                    "lottery_desc": lottery_type,
                    "home": "曼城", # mock
                    "away": "阿森纳" # mock
                }
            }
            
            # 使用调度中心执行多智能体工作流
            result = self.orchestrator.process(task)
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def query_intelligence(self, query: str) -> Dict[str, Any]:
        logger.info(f"Querying intelligence via ScoutAgent: {query}")
        try:
            # 单独调用 scout 智能体
            task = {
                "action": "gather_intelligence",
                "params": {"query": query}
            }
            result = self.orchestrator.registered_agents["scout"].process(task)
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenClaw Main Agent (Native Multi-Agent)")
    parser.add_argument("--lottery", default="JINGCAI", choices=["JINGCAI", "BEIDAN", "ZUCAI"])
    parser.add_argument("--date", default="2026-04-16", help="YYYY-MM-DD")
    parser.add_argument("--online", action="store_true")
    
    args = parser.parse_args()
    
    agent = OpenClawMainAgent(online=args.online)
    result = asyncio.run(agent.analyze_and_trade(args.lottery, args.date))
    print(json.dumps(result, indent=2, ensure_ascii=False))
